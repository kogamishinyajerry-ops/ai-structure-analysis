"""自然语言解析器

使用GPT-4解析后处理指令。
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from openai import OpenAI

from ..core.config import settings


class IntentType(str, Enum):
    """意图类型枚举"""
    VISUALIZE = "visualize"      # 可视化
    EXTRACT = "extract"          # 提取数据
    COMPARE = "compare"          # 对比分析
    VERIFY = "verify"            # 验证判断
    REPORT = "report"            # 生成报告
    QUERY = "query"              # 查询信息
    SIMULATE = "simulate"        # 运行模拟
    OPTIMIZE = "optimize"        # 运行优化/参数敏感性研究



class NLPResult(BaseModel):
    """自然语言解析结果"""
    
    # 基本信息
    original_text: str = Field(..., description="原始输入文本")
    parse_time: float = Field(..., description="解析耗时(秒)")
    success: bool = Field(..., description="解析是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 意图识别
    intent: Optional[IntentType] = Field(None, description="识别的意图")
    confidence: Optional[float] = Field(None, description="置信度")
    
    # 参数提取
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="提取的参数"
    )
    
    # 目标对象
    target_fields: List[str] = Field(
        default_factory=list,
        description="目标字段列表"
    )
    
    # 后续动作
    actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="需要执行的动作列表"
    )


class NLParser:
    """自然语言解析器
    
    使用GPT-4解析后处理相关指令。
    
    支持的指令类型:
    1. 可视化: "显示von Mises应力云图"
    2. 提取: "提取最大应力位置"
    3. 对比: "对比空载和满载情况"
    4. 验证: "检查最大应力是否超标"
    5. 报告: "生成分析报告"
    6. 模拟: "按500N载荷重新运行分析"
    7. 优化: "分析载荷在100N到500N的敏感性"
    """
    
    def __init__(self):
        """初始化解析器"""
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.model = settings.openai_model
        
        # 意图识别提示词
        self.intent_prompt = """你是一个有限元分析后处理助手的意图识别引擎。

用户输入: "{user_input}"

请分析用户的意图并提取参数,返回JSON格式:

{{
  "intent": "visualize|extract|compare|verify|report|query|simulate|optimize",
  "confidence": 0.0-1.0,
  "parameters": {{
    "field": "字段名(如: von_mises, displacement, stress)",
    "plot_type": "云图类型(如: contour, vector)",
    "location": "位置(如: mid_span, maximum)",
    "threshold": "阈值(用于验证)",
    "comparison_items": ["项目1", "项目2"],
    "target_param": "目标参数(如: load, elastic_modulus)",
    "value": "具体数值(simulate用)",
    "range": ["最小值", "最大值", "步数"]
  }},
  "target_fields": ["目标字段1", "目标字段2"],
  "actions": [
    {{
      "action_type": "动作类型(如: run_simulation, run_study)",
      "parameters": {{}},
      "description": "动作描述"
    }}
  ]
}}

意图类型说明:
- visualize: 可视化展示(云图、向量图等)
- extract: 提取数据(最大值、位置等)
- compare: 对比分析(多工况对比)
- verify: 验证判断(是否满足条件)
- report: 生成报告
- query: 查询信息
- simulate: 运行单次新的模拟计算
- optimize: 运行参数敏感性优化研究

示例:
输入: "显示von Mises应力云图"
输出: {{"intent": "visualize", "confidence": 0.95, "parameters": {{"field": "von_mises", "plot_type": "contour"}}, "target_fields": ["von_mises"], "actions": [{{"action_type": "plot_contour", "parameters": {{"field": "von_mises"}}}}]}}

输入: "提取最大应力位置和数值"
输出: {{"intent": "extract", "confidence": 0.92, "parameters": {{"field": "stress", "location": "maximum"}}, "target_fields": ["stress"], "actions": [{{"action_type": "find_maximum", "parameters": {{"field": "stress"}}}}]}}

请返回JSON格式结果:"""
    
    def parse(self, text: str, context: Optional[Dict[str, Any]] = None) -> NLPResult:
        """解析自然语言指令
        
        Args:
            text: 用户输入文本
            context: 上下文信息(可选)
            
        Returns:
            NLPResult: 解析结果
        """
        import time
        start_time = time.time()
        
        # 如果没有API Key,返回错误提示
        if not self.client:
            parse_time = time.time() - start_time
            return NLPResult(
                original_text=text,
                parse_time=parse_time,
                success=False,
                error_message="未配置OPENAI_API_KEY,无法使用NLP功能"
            )
        
        try:
            # 调用GPT-4进行意图识别
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的有限元分析后处理助手。"
                    },
                    {
                        "role": "user",
                        "content": self.intent_prompt.format(user_input=text)
                    }
                ],
                temperature=0.3,  # 降低随机性
                response_format={"type": "json_object"}
            )
            
            # 解析GPT-4返回的JSON
            result_json = json.loads(response.choices[0].message.content)
            
            parse_time = time.time() - start_time
            
            # 构建返回对象
            intent_str = result_json.get("intent", "query")
            intent = IntentType(intent_str) if intent_str in [e.value for e in IntentType] else IntentType.QUERY
            
            return NLPResult(
                original_text=text,
                parse_time=parse_time,
                success=True,
                intent=intent,
                confidence=result_json.get("confidence", 0.5),
                parameters=result_json.get("parameters", {}),
                target_fields=result_json.get("target_fields", []),
                actions=result_json.get("actions", [])
            )
            
        except Exception as e:
            parse_time = time.time() - start_time
            return NLPResult(
                original_text=text,
                parse_time=parse_time,
                success=False,
                error_message=f"解析错误: {str(e)}"
            )
    
    def parse_batch(self, texts: List[str]) -> List[NLPResult]:
        """批量解析文本
        
        Args:
            texts: 文本列表
            
        Returns:
            List[NLPResult]: 解析结果列表
        """
        return [self.parse(text) for text in texts]
    
    def get_supported_intents(self) -> List[str]:
        """获取支持的意图类型列表"""
        return [intent.value for intent in IntentType]
