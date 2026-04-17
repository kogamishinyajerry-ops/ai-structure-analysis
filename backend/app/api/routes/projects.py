from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ...db.session import get_db
from ...models.persistence import Project

router = APIRouter(prefix="/projects", tags=["项目管理"])

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("", response_model=List[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    """获取所有项目"""
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return result.scalars().all()

@router.post("", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """创建新项目"""
    # 检查重名
    existing = await db.execute(select(Project).where(Project.name == project.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="项目名称已存在")
        
    new_project = Project(
        name=project.name,
        description=project.description
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return new_project
