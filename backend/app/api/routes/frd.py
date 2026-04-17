"""结果解析API路由

提供完整的结果文件解析接口
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from pathlib import Path
import tempfile

router = APIRouter(prefix="/results", tags=["结果解析"])


class FRDParseResponse(BaseModel):
    """FRD解析响应"""
    success: bool
    file_name: str
    file_size: int
    parse_time: float
    node_count: int
    element_count: int
    max_displacement: Optional[float] = None
    max_von_mises: Optional[float] = None
    has_displacements: bool
    has_stresses: bool
    has_strains: bool
    error_message: Optional[str] = None


class StressDetail(BaseModel):
    """应力详情"""
    node_id: int
    max_principal: Optional[float] = None
    mid_principal: Optional[float] = None
    min_principal: Optional[float] = None
    von_mises: Optional[float] = None
    Tresca: Optional[float] = None


class NodeDisplacement(BaseModel):
    """节点位移"""
    node_id: int
    x: float
    y: float
    z: float
    magnitude: float


@router.post("/parse/frd", response_model=FRDParseResponse)
async def parse_frd_file(file: UploadFile = File(...)):
    """解析CalculiX .frd文件

    上传并解析CalculiX结果文件(.frd格式)
    """
    try:
        # 保存上传文件到临时目录
        with tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.frd',
            delete=False
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # 解析文件
            from app.parsers.frd_parser import FRDParser
            parser = FRDParser()
            result = parser.parse(tmp_path)

            return FRDParseResponse(
                success=result.success,
                file_name=result.file_name,
                file_size=result.file_size,
                parse_time=result.parse_time,
                node_count=len(result.nodes),
                element_count=len(result.elements),
                max_displacement=result.max_displacement,
                max_von_mises=result.max_von_mises,
                has_displacements=len(result.displacements) > 0,
                has_stresses=len(result.stresses) > 0,
                has_strains=len(result.strains) > 0,
                error_message=result.error_message
            )

        finally:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frd/{file_path:path}/nodes", response_model=dict)
async def get_frd_nodes(file_path: str):
    """获取FRD文件的节点数据"""
    try:
        from app.parsers.frd_parser import FRDParser
        parser = FRDParser()
        result = parser.parse(file_path)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)

        nodes = [
            {
                "node_id": node_id,
                "x": coords[0],
                "y": coords[1],
                "z": coords[2]
            }
            for node_id, coords in result.nodes.items()
        ]

        return {
            "success": True,
            "node_count": len(nodes),
            "nodes": nodes
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frd/{file_path:path}/displacements", response_model=dict)
async def get_frd_displacements(file_path: str):
    """获取FRD文件的位移数据"""
    try:
        from app.parsers.frd_parser import FRDParser
        parser = FRDParser()
        result = parser.parse(file_path)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)

        displacements = []
        for node_id, disp in result.displacements.items():
            magnitude = (disp[0]**2 + disp[1]**2 + disp[2]**2)**0.5
            displacements.append({
                "node_id": node_id,
                "x": disp[0],
                "y": disp[1],
                "z": disp[2],
                "magnitude": magnitude
            })

        # 按magnitude排序
        displacements.sort(key=lambda d: d["magnitude"], reverse=True)

        return {
            "success": True,
            "node_count": len(displacements),
            "max_displacement": result.max_displacement,
            "displacements": displacements
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frd/{file_path:path}/stresses", response_model=dict)
async def get_frd_stresses(file_path: str):
    """获取FRD文件的应力数据"""
    try:
        from app.parsers.frd_parser import FRDParser
        parser = FRDParser()
        result = parser.parse(file_path)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)

        stresses = []
        for node_id, stress in result.stresses.items():
            stresses.append({
                "node_id": node_id,
                "S11": stress.S11,
                "S22": stress.S22,
                "S33": stress.S33,
                "S12": stress.S12,
                "S13": stress.S13,
                "S23": stress.S23,
                "max_principal": stress.max_principal,
                "mid_principal": stress.mid_principal,
                "min_principal": stress.min_principal,
                "von_mises": stress.von_mises,
                "Tresca": stress.Tresca
            })

        # 按von_mises排序
        stresses.sort(
            key=lambda s: s.get("von_mises") or 0,
            reverse=True
        )

        return {
            "success": True,
            "node_count": len(stresses),
            "max_von_mises": result.max_von_mises,
            "stresses": stresses
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))