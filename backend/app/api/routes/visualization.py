"""可视化API路由

提供有限元结果可视化接口
"""
import base64
from io import BytesIO
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from pathlib import Path

from ...services.visualization import get_visualization_service

router = APIRouter(prefix="/visualize", tags=["可视化"])


class VisualizeRequest(BaseModel):
    """可视化请求"""
    result_file: str = Field(..., description="结果文件路径")
    plot_type: str = Field(
        default="displacement",
        description="绘图类型: displacement, stress, deformed"
    )
    component: str = Field(
        default="magnitude",
        description="分量: x, y, z, magnitude"
    )
    deformation_scale: float = Field(
        default=1.0,
        ge=0.0,
        le=1000.0,
        description="变形放大系数"
    )
    increment_index: int = Field(0, description="结果增量索引 (用于模态/屈曲分析)")
    output_format: str = Field(
        default="png",
        description="输出格式: png, jpg, svg, html"
    )


class VisualizeResponse(BaseModel):
    """可视化响应"""
    success: bool
    plot_type: str
    file_path: Optional[str] = None
    image_base64: Optional[str] = None
    html_content: Optional[str] = None
    message: str


_viz_service = None


def get_viz_service():
    """获取可视化服务"""
    global _viz_service
    if _viz_service is None:
        from app.services.visualization import get_visualization_service
        _viz_service = get_visualization_service()
    return _viz_service


@router.post("/plot", response_model=VisualizeResponse)
async def create_visualization(request: VisualizeRequest):
    """创建可视化图像

    根据结果文件生成可视化图像
    """
    try:
        viz = get_visualization_service()

        if not viz.is_available:
            raise HTTPException(
                status_code=503,
                detail="PyVista未安装,可视化功能不可用"
            )

        # 解析结果文件
        from app.parsers.frd_parser import FRDParser
        parser = FRDParser()
        result = parser.parse(request.result_file)

        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=f"结果文件解析失败: {result.error_message}"
            )

        # 生成输出路径
        output_path = Path(f"/tmp/visualization_{result.file_name}.{request.output_format}")

        if request.output_format == "html":
             # We generate HTML by skipping the usual image builders and calling export_scene_as_html
             html_str = viz.export_scene_as_html(
                 parse_result=result, 
                 field=request.component if request.plot_type == "stress" else "VonMises"
             )
             if html_str:
                 from fastapi.responses import HTMLResponse
                 return HTMLResponse(content=html_str)
             else:
                 raise HTTPException(status_code=500, detail="HTML生成失败")

        # 根据类型生成可视化
        # 如果是模态分析，从指定的增量中提取数据
        inc_idx = request.increment_index
        target_displacements = result.displacements
        target_stresses = result.stresses
        
        if result.increments and inc_idx < len(result.increments):
            inc = result.increments[inc_idx]
            target_displacements = inc.displacements
            target_stresses = inc.stresses

        if request.plot_type == "displacement":
            file_path = viz.create_displacement_plot(
                nodes={n.node_id: n.coords for n in result.nodes.values()},
                displacements=target_displacements,
                title=f"位移分布 (增量 {inc_idx})",
                output_path=str(output_path),
                component=request.component
            )
        elif request.plot_type == "stress":
            file_path = viz.create_stress_plot(
                nodes={n.node_id: n.coords for n in result.nodes.values()},
                stresses=target_stresses,
                title=f"应力分布 (增量 {inc_idx})",
                output_path=str(output_path),
                stress_component=request.component
            )
        elif request.plot_type == "deformed":
            file_path = viz.create_deformed_shape(
                nodes={n.node_id: n.coords for n in result.nodes.values()},
                displacements=target_displacements,
                elements={e.element_id: e.nodes for e in result.elements.values()},
                deformation_scale=request.deformation_scale,
                title=f"变形图 (增量 {inc_idx})",
                output_path=str(output_path)
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的绘图类型: {request.plot_type}"
            )

        if file_path:
            # 返回文件路径
            return VisualizeResponse(
                success=True,
                plot_type=request.plot_type,
                file_path=file_path,
            )

    except Exception as e:
        logger.error(f"Visualization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/delta")
async def get_delta_visualization(file1: str, file2: str, component: str = "VonMises"):
    """比较两个结果文件的差异并生成可视化"""
    try:
        viz = get_visualization_service()
        from ...parsers.frd_parser import FRDParser
        parser = FRDParser()
        
        res1 = parser.parse(file1)
        res2 = parser.parse(file2)
        
        if not res1.success or not res2.success:
            raise HTTPException(status_code=400, detail="解析文件失败")
            
        # 验证节点是否一致
        if len(res1.nodes) != len(res2.nodes):
            raise HTTPException(status_code=400, detail="模型拓扑不一致，无法直接比较")
            
        # 创建差异结果对象
        from copy import deepcopy
        delta_res = deepcopy(res1)
        
        # 1. 位移差异
        for nid in delta_res.displacements:
            if nid in res2.displacements:
                d1 = res1.displacements[nid]
                d2 = res2.displacements[nid]
                delta_res.displacements[nid] = (d2[0]-d1[0], d2[1]-d1[1], d2[2]-d1[2])
        
        # 2. 应力差异
        for nid in delta_res.stresses:
            if nid in res2.stresses:
                s1 = res1.stresses[nid]
                s2 = res2.stresses[nid]
                if s1.von_mises and s2.von_mises:
                    delta_res.stresses[nid].von_mises = s2.von_mises - s1.von_mises
        
        html_str = viz.export_scene_as_html(delta_res, field=component)
        if html_str:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=html_str)
        else:
            raise HTTPException(status_code=500, detail="Delta HTML生成失败")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/available", response_model=dict)
async def check_visualization_available():
    """检查可视化功能是否可用"""
    viz = get_viz_service()
    return {
        "available": viz.is_available,
        "message": "PyVista可视化可用" if viz.is_available else "PyVista未安装"
    }


@router.get("/formats", response_model=dict)
async def get_supported_formats():
    """获取支持的输出格式"""
    return {
        "plot_types": ["displacement", "stress", "deformed"],
        "components": ["x", "y", "z", "magnitude", "von_mises", "max_principal", "min_principal"],
        "output_formats": ["png", "jpg", "svg"],
        "deformation_scale_range": [0.0, 1000.0]
    }