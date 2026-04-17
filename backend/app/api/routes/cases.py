"""用例库API路由
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from ...db.session import get_db
from ...services.case_service import get_case_service
from ...core.config import settings

router = APIRouter(prefix="/cases", tags=["用例库"])

# 黄金样本根目录
GS_ROOT = settings.gs_root

@router.get("", response_model=List[Dict[str, Any]])
async def list_cases(
    project_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取所有可用的用例 (from DB, optionally filtered by project)"""
    case_svc = get_case_service()
    db_cases = await case_svc.list_cases(db, project_id=project_id)
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": f"Structural Analysis Case - {c.structure_type}",
            "type": "Mechanical",
            "structure": c.structure_type,
            "frd_path": c.frd_path
        }
        for c in db_cases
    ]

@router.get("/{case_id}", response_model=Dict[str, Any])
async def get_case_details(case_id: str, db: AsyncSession = Depends(get_db)):
    """获取特定用例的详细信息 (from DB context)"""
    case_svc = get_case_service()
    c = await case_svc.get_case(db, case_id)
    if not c:
        raise HTTPException(status_code=404, detail=f"用例 {case_id} 不存在")
    
    # 尽可能加载原始的 expected_results.json 作为详情补充
    metadata_path = GS_ROOT / case_id / "expected_results.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
            
    return {"case_id": c.id, "case_name": c.name}
