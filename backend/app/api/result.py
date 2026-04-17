"""结果解析API路由"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any

from ..parsers.result_parser import ResultParser

router = APIRouter(prefix="/api/v1", tags=["result"])

# 初始化解析器
result_parser = ResultParser()


@router.post("/parse-result")
async def parse_result_file(
    file: UploadFile = File(..., description="CalculiX结果文件(.frd或.dat)")
) -> Dict[str, Any]:
    """解析CalculiX结果文件
    
    Args:
        file: 上传的结果文件
        
    Returns:
        解析结果,包含:
        - 基本信息(文件名、大小、解析时间)
        - 模型信息(节点数、单元数)
        - 结果数据(位移、应力、应变)
        - 统计信息(最大值等)
    """
    # 检查文件格式
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")
    
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ["frd", "dat"]:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: .{file_ext}, 支持: .frd, .dat"
        )
    
    # 保存上传文件
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # 解析文件
        result = result_parser.parse(tmp_path)
        
        # 返回结果
        return {
            "success": result.success,
            "file_name": result.file_name,
            "file_size": result.file_size,
            "parse_time": result.parse_time,
            "node_count": result.node_count,
            "element_count": result.element_count,
            "max_displacement": result.max_displacement,
            "max_von_mises": result.max_von_mises,
            "max_principal_stress": result.max_principal_stress,
            "error_message": result.error_message
        }
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/supported-formats")
async def get_supported_formats() -> Dict[str, Any]:
    """获取支持的文件格式列表"""
    return {
        "formats": [".frd", ".dat"],
        "description": {
            ".frd": "CalculiX二进制结果文件",
            ".dat": "CalculiX文本结果文件"
        }
    }
