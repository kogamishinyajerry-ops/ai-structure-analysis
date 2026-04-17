import json
import logging
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional

from ..models.persistence import Project, Case
from ..core.config import settings


logger = logging.getLogger(__name__)

class CaseService:
    """用例持久化服务
    
    管理项目和用例，并在启动时自动导入黄金样本
    """

    async def auto_import_golden_samples(self, db: AsyncSession):
        """将 golden_samples 目录下的用例自动导入数据库"""
        # 1. 确保存在默认项目
        result = await db.execute(select(Project).where(Project.name == "Default Project"))
        default_project = result.scalar_one_or_none()
        
        if not default_project:
            default_project = Project(
                name="Default Project", 
                description="自动生成的默认项目，包含系统内置黄金样本"
            )
            db.add(default_project)
            await db.commit()
            await db.refresh(default_project)

        # 2. 扫描目录并导入
        if not settings.gs_root.exists():
            return

        for item in settings.gs_root.iterdir():
            if item.is_dir() and item.name.startswith("GS-"):
                # 检查是否已存在
                check_res = await db.execute(select(Case).where(Case.id == item.name))
                if check_res.scalar_one_or_none():
                    continue

                metadata_path = item / "expected_results.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            new_case = Case(
                                id=item.name,
                                project_id=default_project.id,
                                name=data.get("case_name"),
                                structure_type=data.get("structure_type", "continuum"),
                                frd_path=str(item / f"{item.name.lower()}.inp"), # 或者其它默认路径
                                status="IDLE"
                            )
                            db.add(new_case)
                            logger.info(f"Auto-imported case: {item.name}")
                    except Exception as e:
                        logger.error(f"Failed to import {item.name}: {e}")
        
        await db.commit()

    async def list_cases(self, db: AsyncSession, project_id: Optional[int] = None) -> List[Case]:
        """获取所有用例"""
        query = select(Case)
        if project_id:
            query = query.where(Case.project_id == project_id)
        
        result = await db.execute(query.order_by(Case.id))
        return list(result.scalars().all())

    async def get_case(self, db: AsyncSession, case_id: str) -> Optional[Case]:
        """获取特定用例"""
        result = await db.execute(select(Case).where(Case.id == case_id))
        return result.scalar_one_or_none()

# 单例
_case_service = None

def get_case_service():
    global _case_service
    if _case_service is None:
        _case_service = CaseService()
    return _case_service
