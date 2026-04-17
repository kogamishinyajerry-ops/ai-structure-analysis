# Sprint 2 功能演示

**日期**: 2026-04-08
**版本**: 0.2.0

---

## 🎯 演示内容

Sprint 2 新增功能演示:
1. ChromaDB知识库检索
2. FRD完整解析
3. API端点展示

---

## 📦 演示1: ChromaDB知识库

```python
from app.services.knowledge_base import get_fea_knowledge_base

# 获取知识库
kb = get_fea_knowledge_base()

# 查询相关知识
results = kb.query("什么是von Mises应力", top_k=3)

print(f"找到{len(results)}条相关知识:")
for r in results:
    print(f"  相似度: {r.score:.2f}")
    print(f"  内容: {r.content[:50]}...")
```

**预期输出**:
```
找到3条相关知识:
  相似度: 0.95
  内容: von Mises应力: 用于屈服判据的等效应力...
```

---

## 📊 演示2: FRD完整解析

```python
from app.parsers.frd_parser import FRDParser

parser = FRDParser()
result = parser.parse("results.frd")

print(f"节点数: {len(result.nodes)}")
print(f"单元数: {len(result.elements)}")
print(f"位移数: {len(result.displacements)}")
print(f"应力数: {len(result.stresses)}")
print(f"最大位移: {result.max_displacement:.6e} m")
print(f"最大von Mises: {result.max_von_mises:.6e} Pa")
```

**预期输出**:
```
节点数: 1000
单元数: 500
位移数: 1000
应力数: 1000
最大位移: 1.234567e-03 m
最大von Mises: 5.678901e+07 Pa
```

---

## 🌐 演示3: API端点

启动服务后访问:

```
http://localhost:8000/docs
```

**新增端点**:

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/knowledge/query` | POST | 知识检索 |
| `/api/v1/knowledge/rag` | POST | RAG问答 |
| `/api/v1/visualize/plot` | POST | 可视化 |
| `/api/v1/results/parse/frd` | POST | FRD解析 |
| `/api/v1/results/frd/{path}/displacements` | GET | 位移数据 |

---

## 🚀 启动Sprint 2服务

```bash
cd backend
pip install chromadb pyvista  # 安装依赖
uvicorn app.main:app --reload
```

然后访问 http://localhost:8000/docs 查看完整API文档。

---

## 📝 注意事项

1. **PyVista**: 如果未安装,可视化功能不可用但API正常
2. **ChromaDB**: 首次运行会自动加载8个预置知识文档
3. **RAG**: 需要配置OPENAI_API_KEY才能使用完整RAG功能