"""知识库API路由

提供知识检索和RAG问答接口
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/knowledge", tags=["知识库"])


class KnowledgeQuery(BaseModel):
    """知识查询请求"""
    query: str = Field(..., description="查询文本")
    top_k: int = Field(default=3, ge=1, le=10, description="返回结果数量")


class KnowledgeDocument(BaseModel):
    """知识文档"""
    content: str
    metadata: dict
    score: float


class KnowledgeQueryResponse(BaseModel):
    """知识查询响应"""
    success: bool
    query: str
    results: List[KnowledgeDocument]
    count: int


class AddKnowledgeRequest(BaseModel):
    """添加知识请求"""
    content: str = Field(..., description="知识内容")
    category: str = Field(..., description="类别")
    topic: str = Field(..., description="主题")


class RAGQuery(BaseModel):
    """RAG问答请求"""
    question: str = Field(..., description="问题")
    top_k: int = Field(default=3, description="参考知识数量")
    include_context: bool = Field(default=True, description="是否返回参考上下文")


class RAGResponse(BaseModel):
    """RAG问答响应"""
    success: bool
    question: str
    answer: str
    references: List[KnowledgeDocument]
    sources: List[str]


# 延迟导入避免循环依赖
_kb = None
_fea_kb = None


def get_kb():
    """获取知识库实例"""
    global _kb, _fea_kb
    if _kb is None:
        from app._frozen.sprint2.knowledge_base import get_knowledge_base, get_fea_knowledge_base
        _kb = get_knowledge_base()
        _fea_kb = get_fea_knowledge_base()
    return _kb, _fea_kb


@router.post("/query", response_model=KnowledgeQueryResponse)
async def query_knowledge(request: KnowledgeQuery):
    """查询相关知识

    根据输入文本检索知识库中的相关内容
    """
    try:
        _, fea_kb = get_kb()

        if not fea_kb.kb.is_available:
            raise HTTPException(
                status_code=503,
                detail="知识库服务不可用"
            )

        # 检索知识
        results = fea_kb.query(request.query, top_k=request.top_k)

        # 构建响应
        documents = [
            KnowledgeDocument(
                content=r.content,
                metadata=r.metadata,
                score=r.score
            )
            for r in results
        ]

        return KnowledgeQueryResponse(
            success=True,
            query=request.query,
            results=documents,
            count=len(documents)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add", response_model=dict)
async def add_knowledge(request: AddKnowledgeRequest):
    """添加知识到知识库

    添加自定义知识文档到向量数据库
    """
    try:
        _, fea_kb = get_kb()

        if not fea_kb.kb.is_available:
            raise HTTPException(
                status_code=503,
                detail="知识库服务不可用"
            )

        # 添加知识
        success = fea_kb.add_custom_knowledge(
            content=request.content,
            category=request.category,
            topic=request.topic
        )

        return {
            "success": success,
            "message": "知识添加成功" if success else "知识添加失败"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=dict)
async def get_knowledge_stats():
    """获取知识库统计信息

    返回知识库中的文档数量等信息
    """
    try:
        kb, _ = get_kb()

        if not kb.is_available:
            raise HTTPException(
                status_code=503,
                detail="知识库服务不可用"
            )

        return {
            "success": True,
            "document_count": kb.count_documents(),
            "collection_name": kb.config.collection_name,
            "available": kb.is_available
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear", response_model=dict)
async def clear_knowledge_base():
    """清空知识库

    删除所有自定义添加的知识(预置知识也会被清除)
    """
    try:
        kb, _ = get_kb()

        if not kb.is_available:
            raise HTTPException(
                status_code=503,
                detail="知识库服务不可用"
            )

        success = kb.clear()

        return {
            "success": success,
            "message": "知识库已清空" if success else "清空失败"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag", response_model=RAGResponse)
async def rag_query(request: RAGQuery):
    """RAG问答

    基于知识库的检索增强问答
    """
    try:
        _, fea_kb = get_kb()

        if not fea_kb.kb.is_available:
            raise HTTPException(
                status_code=503,
                detail="知识库服务不可用"
            )

        # 检索相关知识
        results = fea_kb.query(request.question, top_k=request.top_k)

        if not results:
            return RAGResponse(
                success=True,
                question=request.question,
                answer="抱歉,知识库中没有找到相关信息。",
                references=[],
                sources=[]
            )

        # 构建上下文
        context = "\n\n".join([
            f"参考文档{i+1}:\n{r.content}"
            for i, r in enumerate(results)
        ])

        # 构建提示
        prompt = f"""基于以下参考信息,回答用户的问题。如果参考信息中没有相关内容,请说明无法回答。

参考信息:
{context}

用户问题: {request.question}

回答:"""

        # TODO: 调用GPT生成回答(需要API Key)
        # 这里暂时返回基于检索结果的简单回答
        answer_parts = [r.content for r in results[:1]]
        answer = " ".join(answer_parts) if answer_parts else "无法生成回答"

        references = [
            KnowledgeDocument(
                content=r.content,
                metadata=r.metadata,
                score=r.score
            )
            for r in results
        ]

        sources = [r.metadata.get("category", "unknown") for r in results]

        return RAGResponse(
            success=True,
            question=request.question,
            answer=answer,
            references=references if request.include_context else [],
            sources=list(set(sources))
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))