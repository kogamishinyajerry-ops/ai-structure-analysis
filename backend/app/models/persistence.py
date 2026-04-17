from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, ForeignKey, DateTime, Text, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.session import Base

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    cases: Mapped[List["Case"]] = relationship(back_populates="project", cascade="all, delete-orphan")

class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(50), primary_key=True) # GS-001 等
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(100))
    structure_type: Mapped[str] = mapped_column(String(50)) # Truss, Beam, etc.
    frd_path: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="IDLE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    project: Mapped["Project"] = relationship(back_populates="cases")
    jobs: Mapped[List["SimulationJob"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    messages: Mapped[List["ChatMessage"]] = relationship(back_populates="case", cascade="all, delete-orphan")

class SimulationJob(Base):
    __tablename__ = "simulation_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    job_id: Mapped[str] = mapped_column(String(100))
    run_type: Mapped[str] = mapped_column(String(20)) # SOLVER, SENSITIVITY
    status: Mapped[str] = mapped_column(String(20)) # RUNNING, COMPLETED, FAILED
    metrics: Mapped[Optional[dict]] = mapped_column(JSON) # 存储 stress, displacement 等结果
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    case: Mapped["Case"] = relationship(back_populates="jobs")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    role: Mapped[str] = mapped_column(String(20)) # user, assistant
    content: Mapped[str] = mapped_column(Text)
    action_json: Mapped[Optional[dict]] = mapped_column(JSON) # 存储 Copilot 建议的动作
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    case: Mapped["Case"] = relationship(back_populates="messages")
