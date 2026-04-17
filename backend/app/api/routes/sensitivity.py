from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

from ...core.config import settings
from ...services.sensitivity import get_sensitivity_service

GS_ROOT = settings.gs_root

router = APIRouter(prefix="/sensitivity", tags=["敏感性分析"])

class StudyRequest(BaseModel):
    case_id: str
    parameter: str # 'load' or 'elastic_modulus'
    values: List[float]

class StudyResponse(BaseModel):
    experiment_id: str
    status: str
    run_count: int

@router.post("/run", response_model=StudyResponse)
async def start_study(request: StudyRequest):
    """启动参数敏感性研究"""
    base_inp = GS_ROOT / request.case_id / f"{request.case_id.lower()}.inp"
    
    if not base_inp.exists():
        raise HTTPException(status_code=404, detail=f"找不到基础输入文件: {base_inp}")
        
    if request.parameter not in ['load', 'elastic_modulus']:
        raise HTTPException(status_code=400, detail="不支持的参数类型")

    service = get_sensitivity_service()
    exp_id = await service.run_study(base_inp, request.parameter, request.values)
    
    return StudyResponse(
        experiment_id=exp_id,
        status="RUNNING",
        run_count=len(request.values)
    )

@router.get("/status/{exp_id}")
async def get_study_status(exp_id: str):
    """查询实验组状态"""
    service = get_sensitivity_service()
    status = service.get_experiment_status(exp_id)
    if not status:
        raise HTTPException(status_code=404, detail="实验不存在")
    return status
