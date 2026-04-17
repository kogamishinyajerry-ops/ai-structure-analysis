"""自然语言解析API路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from ..parsers.nl_parser import NLParser, IntentType
from ..services.copilot import get_copilot_service
from ..db.session import get_db
from ..models.persistence import ChatMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

router = APIRouter(prefix="/api/v1", tags=["nlp"])

# 初始化解析器
nl_parser = NLParser()


class NLParseRequest(BaseModel):
    """自然语言解析请求"""
    text: str = Field(..., description="用户输入的自然语言指令")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="上下文信息(如当前任务ID、已加载的结果等)"
    )


class NLParseResponse(BaseModel):
    """自然语言解析响应"""
    success: bool = Field(..., description="解析是否成功")
    original_text: str = Field(..., description="原始输入文本")
    parse_time: float = Field(..., description="解析耗时(秒)")
    intent: Optional[str] = Field(None, description="识别的意图")
    confidence: Optional[float] = Field(None, description="置信度")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="提取的参数")
    target_fields: List[str] = Field(default_factory=list, description="目标字段")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="动作列表")
    error_message: Optional[str] = Field(None, description="错误信息")


@router.post("/parse-nl", response_model=NLParseResponse)
async def parse_natural_language(
    request: NLParseRequest, 
    db: AsyncSession = Depends(get_db)
) -> NLParseResponse:
    """解析自然语言指令并保存对话 (Sprint 9)"""
    # 调用解析器
    result = nl_parser.parse(request.text, request.context)
    
    # 构建响应
    response = NLParseResponse(
        success=result.success,
        original_text=result.original_text,
        parse_time=result.parse_time,
        intent=result.intent.value if result.intent else None,
        confidence=result.confidence,
        parameters=result.parameters,
        target_fields=result.target_fields,
        actions=result.actions,
        error_message=result.error_message
    )

    # 持久化对话 (Sprint 9)
    case_id = request.context.get("case_id") if request.context else None
    if case_id and result.success:
        # 1. 保存用户消息
        user_msg = ChatMessage(
            case_id=case_id,
            role="user",
            content=request.text
        )
        db.add(user_msg)
        
        # 2. 保存助手响应
        bot_content = f"Identized intent: {response.intent}. " + (result.actions[0].get("description", "") if result.actions else "")
        bot_msg = ChatMessage(
            case_id=case_id,
            role="assistant",
            content=bot_content,
            action_json=result.actions[0] if result.actions else None
        )
        db.add(bot_msg)
        await db.commit()

    return response


@router.post("/parse-nl/batch")
async def parse_natural_language_batch(
    texts: List[str]
) -> List[NLParseResponse]:
    """批量解析自然语言指令
    
    Args:
        texts: 文本列表
        
    Returns:
        解析结果列表
    """
    results = nl_parser.parse_batch(texts)
    
    return [
        NLParseResponse(
            success=r.success,
            original_text=r.original_text,
            parse_time=r.parse_time,
            intent=r.intent.value if r.intent else None,
            confidence=r.confidence,
            parameters=r.parameters,
            target_fields=r.target_fields,
            actions=r.actions,
            error_message=r.error_message
        )
        for r in results
    ]


@router.get("/supported-intents")
async def get_supported_intents() -> Dict[str, Any]:
    """获取支持的意图类型列表"""
    return {
        "intents": [
            {
                "type": "visualize",
                "description": "可视化展示(云图、向量图等)",
                "examples": ["显示von Mises应力云图", "绘制位移矢量图"]
            },
            {
                "type": "extract",
                "description": "提取数据(最大值、位置等)",
                "examples": ["提取最大应力位置", "获取跨中位移"]
            },
            {
                "type": "compare",
                "description": "对比分析(多工况对比)",
                "examples": ["对比空载和满载情况", "比较两种材料的应力分布"]
            },
            {
                "type": "verify",
                "description": "验证判断(是否满足条件)",
                "examples": ["检查最大应力是否超标", "验证位移是否满足规范要求"]
            },
            {
                "type": "report",
                "description": "生成报告",
                "examples": ["生成分析报告", "输出结果摘要"]
            },
            {
                "type": "query",
                "description": "查询信息",
                "examples": ["最大位移是多少", "材料参数是什么"]
            }
        ]
    }

class ExecuteRequest(BaseModel):
    action: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None

@router.post("/execute")
async def execute_copilot_action(request: ExecuteRequest):
    """执行副驾驶建议的动作"""
    service = get_copilot_service()
    result = await service.execute_action(request.action, request.context)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

@router.get("/history/{case_id}")
async def get_chat_history(case_id: str, db: AsyncSession = Depends(get_db)):
    """获取特定用例的对话历史"""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.case_id == case_id)
        .order_by(ChatMessage.created_at.asc())
    )
    res = await db.execute(stmt)
    messages = res.scalars().all()
    
    return [
        {
            "role": m.role,
            "content": m.content,
            "proposedAction": m.action_json,
            "created_at": m.created_at
        }
        for m in messages
    ]
