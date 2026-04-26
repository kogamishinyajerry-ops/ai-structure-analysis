"""知识库服务 - ChromaDB向量数据库 + RAG检索

提供有限元领域知识的存储和检索功能:
- 知识文档向量化
- 语义检索
- RAG问答
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeDocument:
    """知识文档"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    metadata: Dict[str, Any]
    score: float
    distance: float


@dataclass
class KnowledgeBaseConfig:
    """知识库配置"""
    persist_directory: str = "./data/knowledge_base"
    collection_name: str = "fea_knowledge"
    embedding_model: str = "text-embedding-ada-002"
    chunk_size: int = 500
    chunk_overlap: int = 50


class ChromaKnowledgeBase:
    """ChromaDB知识库

    使用ChromaDB实现向量存储和检索
    """

    def __init__(self, config: Optional[KnowledgeBaseConfig] = None):
        """初始化知识库

        Args:
            config: 知识库配置
        """
        self.config = config or KnowledgeBaseConfig()
        self._client = None
        self._collection = None
        self._initialized = False

        # 延迟初始化
        self._initialize()

    def _initialize(self) -> None:
        """初始化ChromaDB连接"""
        try:
            import chromadb
            from chromadb.config import Settings

            # 创建持久化目录
            persist_dir = Path(self.config.persist_directory)
            persist_dir.mkdir(parents=True, exist_ok=True)

            # 初始化客户端
            self._client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )

            # 获取或创建集合
            self._collection = self._client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"description": "有限元分析知识库"}
            )

            self._initialized = True
            logger.info(f"知识库初始化成功: {self.config.collection_name}")

        except ImportError:
            logger.warning("ChromaDB未安装,使用模拟模式")
            self._initialized = False
        except Exception as e:
            logger.error(f"知识库初始化失败: {e}")
            self._initialized = False

    @property
    def is_available(self) -> bool:
        """检查知识库是否可用"""
        return self._initialized

    def add_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None
    ) -> bool:
        """添加文档到知识库

        Args:
            content: 文档内容
            metadata: 文档元数据
            document_id: 文档ID(可选)

        Returns:
            是否添加成功
        """
        if not self._initialized:
            logger.warning("知识库未初始化,文档添加失败")
            return False

        try:
            import uuid

            doc_id = document_id or str(uuid.uuid4())
            meta = metadata or {}

            # 添加文档
            self._collection.add(
                documents=[content],
                metadatas=[meta],
                ids=[doc_id]
            )

            logger.info(f"文档添加成功: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"文档添加失败: {e}")
            return False

    def add_documents_batch(
        self,
        documents: List[Tuple[str, Dict[str, Any]]]
    ) -> bool:
        """批量添加文档

        Args:
            documents: [(content, metadata), ...] 列表

        Returns:
            是否添加成功
        """
        if not self._initialized:
            logger.warning("知识库未初始化,文档添加失败")
            return False

        try:
            import uuid

            contents = []
            metadatas = []
            ids = []

            for content, metadata in documents:
                contents.append(content)
                metadatas.append(metadata or {})
                ids.append(str(uuid.uuid4()))

            self._collection.add(
                documents=contents,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"批量添加{len(documents)}个文档成功")
            return True

        except Exception as e:
            logger.error(f"批量文档添加失败: {e}")
            return False

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """检索相关文档

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filters: 元数据过滤器

        Returns:
            检索结果列表
        """
        if not self._initialized:
            logger.warning("知识库未初始化,返回空结果")
            return []

        try:
            # 执行查询
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filters
            )

            # 解析结果
            retrieval_results = []
            if results and 'documents' in results:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if 'metadatas' in results else {}
                    distance = results['distances'][0][i] if 'distances' in results else 0.0

                    # 将距离转换为相似度分数
                    score = 1.0 / (1.0 + distance)

                    retrieval_results.append(RetrievalResult(
                        content=doc,
                        metadata=metadata,
                        score=score,
                        distance=distance
                    ))

            return retrieval_results

        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []

    def get_document(self, document_id: str) -> Optional[KnowledgeDocument]:
        """获取单个文档

        Args:
            document_id: 文档ID

        Returns:
            文档内容,不存在返回None
        """
        if not self._initialized:
            return None

        try:
            result = self._collection.get(ids=[document_id])

            if result and 'documents' in result and result['documents']:
                return KnowledgeDocument(
                    id=document_id,
                    content=result['documents'][0],
                    metadata=result['metadatas'][0] if 'metadatas' in result else {},
                    embedding=None
                )

            return None

        except Exception as e:
            logger.error(f"获取文档失败: {e}")
            return None

    def delete_document(self, document_id: str) -> bool:
        """删除文档

        Args:
            document_id: 文档ID

        Returns:
            是否删除成功
        """
        if not self._initialized:
            return False

        try:
            self._collection.delete(ids=[document_id])
            return True

        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    def count_documents(self) -> int:
        """获取文档数量"""
        if not self._initialized:
            return 0

        try:
            return self._collection.count()
        except:
            return 0

    def clear(self) -> bool:
        """清空知识库"""
        if not self._initialized:
            return False

        try:
            self._client.delete_collection(self.config.collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self.config.collection_name
            )
            return True

        except Exception as e:
            logger.error(f"清空知识库失败: {e}")
            return False


class FEAKnowledgeBase:
    """有限元分析专业知识库

    预置有限元领域知识
    """

    # 预置知识文档
    KNOWLEDGE_DOCS = [
        {
            "content": "梁单元理论: Euler-Bernoulli梁理论假设横截面保持平面且垂直于中性轴。弯曲应力公式σ = My/I,其中M为弯矩,y为距中性轴距离,I为截面惯性矩。",
            "metadata": {"category": "theory", "topic": "beam theory"}
        },
        {
            "content": "von Mises应力: 用于屈服判据的等效应力,公式为σ_vm = √[(S1-S2)² + (S2-S3)² + (S3-S1)²]/2,其中S1,S2,S3为主应力。",
            "metadata": {"category": "theory", "topic": "stress"}
        },
        {
            "content": "位移边界条件: 在有限元分析中,位移边界条件用于约束模型刚体位移。常见类型包括固定约束、简支约束、对称约束等。",
            "metadata": {"category": "boundary conditions", "topic": "displacement"}
        },
        {
            "content": "收敛准则: 有限元求解的收敛准则通常包括力准则和位移准则。力准则检查残差力,位移准则检查位移增量。",
            "metadata": {"category": "solver", "topic": "convergence"}
        },
        {
            "content": "单元类型选择: 实体单元(C3D8,C3D4)适用于三维应力分析,壳单元(S4,S3)适用于薄壁结构,梁单元(B31,B32)适用于细长构件。",
            "metadata": {"category": "elements", "topic": "element selection"}
        },
        {
            "content": "网格收敛性: 网格加密可提高计算精度,但计算成本增加。建议进行网格敏感性分析,找到精度和成本的平衡点。",
            "metadata": {"category": "meshing", "topic": "convergence"}
        },
        {
            "content": "应力集中: 几何不连续处(如孔、缺口、突变截面)会产生应力集中。理论应力集中系数Kt可通过手册查询或有限元分析确定。",
            "metadata": {"category": "stress", "topic": "stress concentration"}
        },
        {
            "content": "CalculiX是一款开源有限元软件,支持静力学、动力学、热力耦合等分析。输入格式包括.inp(ABAQUS兼容)和.frd(结果文件)。",
            "metadata": {"category": "software", "topic": "CalculiX"}
        },
    ]

    def __init__(self, kb: ChromaKnowledgeBase):
        """初始化有限元知识库

        Args:
            kb: ChromaDB知识库实例
        """
        self.kb = kb
        self._load_knowledge()

    def _load_knowledge(self) -> None:
        """加载预置知识"""
        if not self.kb.is_available:
            logger.warning("知识库不可用,跳过知识加载")
            return

        # 检查是否已加载
        if self.kb.count_documents() > 0:
            logger.info(f"知识库已有{self.kb.count_documents()}个文档")
            return

        # 批量添加知识文档
        docs = [(d["content"], d["metadata"]) for d in self.KNOWLEDGE_DOCS]
        self.kb.add_documents_batch(docs)
        logger.info(f"已加载{len(self.KNOWLEDGE_DOCS)}个预置知识文档")

    def query(self, question: str, top_k: int = 3) -> List[RetrievalResult]:
        """查询相关知识

        Args:
            question: 问题文本
            top_k: 返回结果数量

        Returns:
            检索结果
        """
        return self.kb.retrieve(question, top_k=top_k)

    def add_custom_knowledge(
        self,
        content: str,
        category: str,
        topic: str
    ) -> bool:
        """添加自定义知识

        Args:
            content: 知识内容
            category: 类别
            topic: 主题

        Returns:
            是否添加成功
        """
        metadata = {"category": category, "topic": topic}
        return self.kb.add_document(content, metadata)


# 全局实例
_kb_instance: Optional[ChromaKnowledgeBase] = None
_fea_kb_instance: Optional[FEAKnowledgeBase] = None


def get_knowledge_base() -> ChromaKnowledgeBase:
    """获取知识库单例"""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = ChromaKnowledgeBase()
    return _kb_instance


def get_fea_knowledge_base() -> FEAKnowledgeBase:
    """获取有限元知识库单例"""
    global _fea_kb_instance
    if _fea_kb_instance is None:
        _fea_kb_instance = FEAKnowledgeBase(get_knowledge_base())
    return _fea_kb_instance