"""TaskSpec - 任务规格对象

定义有限元分析任务的元数据和约束条件。
"""
from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class TaskType(str, Enum):
    """任务类型枚举"""
    STATIC_ANALYSIS = "static_analysis"
    MODAL_ANALYSIS = "modal_analysis"
    THERMAL_ANALYSIS = "thermal_analysis"
    BUCKLING_ANALYSIS = "buckling_analysis"
    DYNAMIC_ANALYSIS = "dynamic_analysis"


class Priority(str, Enum):
    """优先级枚举"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BoundaryCondition(BaseModel):
    """边界条件"""
    name: str = Field(..., description="边界条件名称")
    type: str = Field(..., description="约束类型: fixed, load, displacement等")
    location: str = Field(..., description="作用位置")
    values: Dict[str, float] = Field(default_factory=dict, description="数值参数")
    unit: str = Field(default="N", description="单位")


class MeshSpec(BaseModel):
    """网格规格"""
    element_type: str = Field(..., description="单元类型")
    element_size: float = Field(..., description="单元尺寸")
    node_count: Optional[int] = Field(None, description="节点数量")
    element_count: Optional[int] = Field(None, description="单元数量")


class TaskSpec(BaseModel):
    """任务规格对象
    
    定义有限元分析任务的完整规格,包括:
    - 任务元数据
    - 边界条件
    - 网格参数
    - 材料属性
    - 求解器设置
    """
    
    # 基本信息
    task_id: str = Field(..., description="任务唯一标识符")
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    task_type: TaskType = Field(..., description="任务类型")
    priority: Priority = Field(default=Priority.MEDIUM, description="优先级")
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    deadline: Optional[datetime] = Field(None, description="截止时间")
    
    # 模型信息
    geometry_file: str = Field(..., description="几何文件路径")
    material_properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="材料属性: E, nu, density等"
    )
    
    # 边界条件
    boundary_conditions: List[BoundaryCondition] = Field(
        default_factory=list,
        description="边界条件列表"
    )
    
    # 网格规格
    mesh_spec: Optional[MeshSpec] = Field(None, description="网格规格")
    
    # 求解器设置
    solver_type: str = Field(default="calculix", description="求解器类型")
    solver_version: str = Field(default="2.19", description="求解器版本")
    solver_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="求解器参数"
    )
    
    # 验收标准
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="验收标准列表"
    )
    
    # 标签
    tags: List[str] = Field(default_factory=list, description="标签列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "GS-001",
                "name": "简支梁静力学分析",
                "description": "验证简支梁在均布载荷下的应力和变形",
                "task_type": "static_analysis",
                "priority": "high",
                "geometry_file": "gs001_geometry.step",
                "material_properties": {
                    "E": 210e9,
                    "nu": 0.3,
                    "density": 7850
                },
                "boundary_conditions": [
                    {
                        "name": "固定端",
                        "type": "fixed",
                        "location": "left_end",
                        "values": {"x": 0, "y": 0, "z": 0}
                    },
                    {
                        "name": "均布载荷",
                        "type": "pressure",
                        "location": "top_surface",
                        "values": {"magnitude": -10000},
                        "unit": "Pa"
                    }
                ],
                "mesh_spec": {
                    "element_type": "C3D8R",
                    "element_size": 0.01,
                    "node_count": 10000
                },
                "acceptance_criteria": [
                    "最大应力 < 材料屈服强度",
                    "最大位移 < 跨度/250"
                ]
            }
        }
