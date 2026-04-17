"""EvidenceBundle - 证据包对象

存储验证判断所需的所有证据项。
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class EvidenceType(str, Enum):
    """证据类型枚举"""
    SIMULATION_RESULT = "simulation_result"
    ANALYTICAL_RESULT = "analytical_result"
    EXPERIMENTAL_DATA = "experimental_data"
    REFERENCE_DATA = "reference_data"
    CALCULATION = "calculation"
    FIGURE = "figure"
    TABLE = "table"


class VerificationStatus(str, Enum):
    """验证状态枚举"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    PENDING = "pending"


class EvidenceItem(BaseModel):
    """单个证据项"""
    
    evidence_id: str = Field(..., description="证据项ID")
    evidence_type: EvidenceType = Field(..., description="证据类型")
    title: str = Field(..., description="证据标题")
    description: str = Field(..., description="证据描述")
    
    # 数据内容
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="证据数据内容"
    )
    
    # 数据来源
    source: str = Field(..., description="数据来源")
    source_file: Optional[str] = Field(None, description="源文件路径")
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    
    # 可信度
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="可信度 [0, 1]"
    )
    
    # 验证信息
    verification_status: Optional[VerificationStatus] = Field(
        None,
        description="验证状态"
    )
    verification_message: Optional[str] = Field(None, description="验证消息")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "evidence_id": "EV-001",
                "evidence_type": "simulation_result",
                "title": "最大von Mises应力",
                "description": "提取自CalculiX结果文件",
                "data": {
                    "value": 150.5,
                    "unit": "MPa",
                    "location": "mid_span_bottom"
                },
                "source": "calculix",
                "source_file": "gs001_result.frd",
                "confidence": 0.95,
                "verification_status": "pass"
            }
        }


class EvidenceBundle(BaseModel):
    """证据包对象
    
    汇总所有相关证据项,用于:
    - 支持验证判断
    - 生成证据链
    - 提供可追溯性
    """
    
    bundle_id: str = Field(..., description="证据包ID")
    task_id: str = Field(..., description="关联任务ID")
    
    # 基本信息
    title: str = Field(..., description="证据包标题")
    description: Optional[str] = Field(None, description="证据包描述")
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    # 证据项列表
    evidence_items: List[EvidenceItem] = Field(
        default_factory=list,
        description="证据项列表"
    )
    
    # 验证结论
    verification_summary: Optional[str] = Field(None, description="验证总结")
    overall_status: Optional[VerificationStatus] = Field(
        None,
        description="整体验证状态"
    )
    
    # 证据链
    evidence_chain: List[str] = Field(
        default_factory=list,
        description="证据推导链(证据ID序列)"
    )
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
    
    def add_evidence(self, evidence: EvidenceItem) -> None:
        """添加证据项"""
        self.evidence_items.append(evidence)
        self.updated_at = datetime.utcnow()
    
    def get_evidence_by_id(self, evidence_id: str) -> Optional[EvidenceItem]:
        """根据ID获取证据项"""
        for item in self.evidence_items:
            if item.evidence_id == evidence_id:
                return item
        return None
    
    def get_evidence_by_type(self, evidence_type: EvidenceType) -> List[EvidenceItem]:
        """根据类型获取证据项"""
        return [
            item for item in self.evidence_items
            if item.evidence_type == evidence_type
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "bundle_id": "BUNDLE-001",
                "task_id": "GS-001",
                "title": "简支梁强度验证证据包",
                "evidence_items": [
                    {
                        "evidence_id": "EV-001",
                        "evidence_type": "simulation_result",
                        "title": "最大von Mises应力",
                        "description": "仿真结果",
                        "data": {"value": 150.5, "unit": "MPa"},
                        "source": "calculix",
                        "confidence": 0.95
                    },
                    {
                        "evidence_id": "EV-002",
                        "evidence_type": "reference_data",
                        "title": "材料屈服强度",
                        "description": "钢材Q235",
                        "data": {"value": 235, "unit": "MPa"},
                        "source": "GB/T 700-2006",
                        "confidence": 1.0
                    }
                ],
                "evidence_chain": ["EV-001", "EV-002"],
                "overall_status": "pass"
            }
        }
