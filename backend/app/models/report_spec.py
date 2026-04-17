"""ReportSpec - 报告规格对象

定义自动化报告的结构和内容要求。
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ReportSection(BaseModel):
    """报告章节"""
    title: str = Field(..., description="章节标题")
    level: int = Field(default=1, ge=1, le=3, description="章节级别")
    content: Optional[str] = Field(None, description="章节内容")
    subsections: List["ReportSection"] = Field(
        default_factory=list,
        description="子章节列表"
    )
    required: bool = Field(default=True, description="是否必需章节")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "1. 模型概述",
                "level": 1,
                "content": "本模型为简支梁静力学分析...",
                "subsections": [
                    {
                        "title": "1.1 几何模型",
                        "level": 2,
                        "content": "梁长1m,截面0.1m×0.1m"
                    }
                ]
            }
        }


class VisualizationSpec(BaseModel):
    """可视化规格"""
    plot_type: str = Field(..., description="图表类型: contour, vector, animation等")
    field: str = Field(..., description="显示字段: von_mises, displacement等")
    view_direction: str = Field(default="isometric", description="视图方向")
    colormap: str = Field(default="jet", description="色图")
    show_deformed: bool = Field(default=True, description="显示变形")
    scale_factor: float = Field(default=1.0, description="变形放大系数")


class ReportSpec(BaseModel):
    """报告规格对象
    
    定义自动化报告的完整结构:
    - 报告元数据
    - 章节结构
    - 可视化要求
    - 输出格式
    """
    
    # 基本信息
    report_id: str = Field(..., description="报告唯一标识符")
    task_id: str = Field(..., description="关联任务ID")
    title: str = Field(..., description="报告标题")
    subtitle: Optional[str] = Field(None, description="报告副标题")
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    generated_at: Optional[datetime] = Field(None, description="生成时间")
    
    # 报告结构
    sections: List[ReportSection] = Field(
        default_factory=list,
        description="报告章节列表"
    )
    
    # 可视化要求
    visualizations: List[VisualizationSpec] = Field(
        default_factory=list,
        description="可视化要求列表"
    )
    
    # 输出格式
    output_format: str = Field(default="pdf", description="输出格式: pdf, docx, html")
    template: str = Field(default="standard", description="报告模板")
    
    # 语言和单位
    language: str = Field(default="zh-CN", description="报告语言")
    unit_system: str = Field(default="SI", description="单位制")
    
    # 审批流程
    reviewers: List[str] = Field(default_factory=list, description="审核人列表")
    approval_status: str = Field(default="draft", description="审批状态")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "report_id": "RPT-001",
                "task_id": "GS-001",
                "title": "简支梁静力学分析报告",
                "subtitle": "结构强度验证",
                "sections": [
                    {
                        "title": "1. 模型概述",
                        "level": 1,
                        "subsections": [
                            {
                                "title": "1.1 几何模型",
                                "level": 2,
                                "content": "梁长1m,截面0.1m×0.1m"
                            },
                            {
                                "title": "1.2 材料属性",
                                "level": 2,
                                "content": "钢材, E=210GPa"
                            }
                        ]
                    },
                    {
                        "title": "2. 结果分析",
                        "level": 1,
                        "subsections": [
                            {
                                "title": "2.1 应力分析",
                                "level": 2
                            }
                        ]
                    }
                ],
                "visualizations": [
                    {
                        "plot_type": "contour",
                        "field": "von_mises",
                        "view_direction": "isometric",
                        "show_deformed": True
                    }
                ],
                "output_format": "pdf"
            }
        }


# 更新forward reference
ReportSection.model_rebuild()
