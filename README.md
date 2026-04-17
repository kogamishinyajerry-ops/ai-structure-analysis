# AI-Structure-FEA 自动化助手

> 有限元分析后处理智能Copilot

代码真相源：
- GitHub 仓库：[kogamishinyajerry-ops/ai-structure-analysis](https://github.com/kogamishinyajerry-ops/ai-structure-analysis)
- Notion 只作为项目控制中枢、任务面和审计面，不作为代码真相源
- 本地 `project_state/`、数据库文件和终端绝对路径都不是给 Notion/Opus 使用的引用源

## 项目概述

AI-Structure-FEA是一款面向结构工程师的智能后处理助手,通过自然语言交互自动完成结果提取、验证判断和报告生成。

## Well Harness 自动化架构

项目现已新增 `well_harness` 自动化编排层，对齐 `cfd-harness-unified` 的核心工作流：

```text
Golden Sample / TaskSpec -> executor -> FRD解析 -> 报告生成 -> 参考值复核 -> project_state -> Notion/GitHub payload
```

- `ReplayExecutor`：直接回放已有 FRD，用于 golden sample 自动验收
- `CalculixExecutor`：本机有 `ccx` 时可发起真实求解
- `project_state/`：沉淀每次执行的输入、输出、artifact 和 handoff
- `control_plane_sync.json`：为 Notion / GitHub 控制面生成稳定 payload

快速运行：

```bash
python3 run_well_harness.py GS-001 GS-002 GS-003
```

启用 Notion 自动登记：

```bash
export NOTION_API_KEY="your-integration-token"
python3 run_well_harness.py GS-001 GS-002 GS-003
```

说明：
- `config/well_harness_control_plane.yaml` 绑定的是当前项目专属 Notion 中枢与数据源
- CLI 会在批次完成后自动把运行结果登记进任务库与会话库
- `python3 sync_well_harness_approvals.py` 会把任务库里的审批结果回写到对应 session 的 `Status` / `Outcome` / `Summary`
- 如果未设置 `NOTION_API_KEY`，运行仍会完成，但会跳过 Notion 回写

详细设计见 `docs/well_harness_architecture.md`。

**当前阶段**: Phase 1 - 后处理Copilot  
**Sprint周期**: Sprint 1 (Week 1-2)  
**核心功能**: 结果文件解析 + 自然语言解析

## 技术栈

### 后端
- **框架**: FastAPI 0.104+
- **求解器**: CalculiX 2.19+
- **解析**: meshio, numpy, scipy
- **可视化**: PyVista 0.38+
- **NLP引擎**: GPT-4 API
- **数据库**: PostgreSQL 15 + MongoDB 7.0 + ChromaDB 0.4

### 前端
- **框架**: React 18+
- **UI**: TypeScript + Tailwind CSS

### 测试
- pytest + pytest-cov
- 测试覆盖率目标: ≥80%

## 项目结构

```
ai-structure-fea/
├── backend/              # 后端代码
│   ├── app/
│   │   ├── models/      # Pydantic Schema
│   │   ├── parsers/     # 解析器模块
│   │   ├── api/         # API路由
│   │   └── core/        # 核心配置
│   ├── tests/           # 测试代码
│   └── requirements.txt
├── frontend/            # 前端代码(后续Sprint)
├── golden_samples/      # 黄金样本测试案例
│   └── GS-001/         # 简支梁静力学分析
├── docs/                # 文档
└── README.md
```

## Sprint 1 目标

### 交付物
- [x] 结果文件解析器 (CalculiX .frd格式)
- [x] 自然语言解析器 (GPT-4集成)
- [x] 核心Schema定义 (TaskSpec, ReportSpec, EvidenceBundle)
- [x] 黄金样本 GS-001

### 验收标准
- 结果文件解析成功率 ≥95%
- 自然语言识别准确率 ≥85%
- 可演示端到端流程
- Benchmark结果记录

## 快速开始

### 环境要求
- Python 3.10+
- CalculiX 2.19+ (可选,用于生成测试数据)
- OpenAI API Key

### 安装

```bash
# 克隆项目
cd /Users/Zhuanz/20260408\ AI\ StructureAnalysis

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
cd backend
pip install -r requirements.txt

# 配置环境变量
export OPENAI_API_KEY="your-api-key"
```

### 运行测试

```bash
cd backend
pytest tests/ -v --cov=app
```

### 启动API服务

```bash
cd backend
uvicorn app.main:app --reload
```

访问 http://localhost:8000/docs 查看API文档

## 开发进度

### Phase 1: 后处理Copilot (Week 1-8)
- **Sprint 1** (Week 1-2): 结果解析 + NLP解析 ← 当前
- Sprint 2 (Week 3-4): 知识检索 + 可视化
- Sprint 3 (Week 5-6): 报告生成 + UI原型
- Sprint 4 (Week 7-8): 集成测试 + 性能优化

## API端点 (Sprint 1)

### 结果解析
```http
POST /api/v1/parse-result
Content-Type: multipart/form-data

file: .frd结果文件
```

### 自然语言解析
```http
POST /api/v1/parse-nl
Content-Type: application/json

{
  "text": "显示von Mises应力云图",
  "context": {...}
}
```

## 贡献指南

本项目采用TDD开发模式:
1. 编写测试用例
2. 实现功能代码
3. 验证测试通过
4. 重构优化

## 许可证

MIT License

## 联系方式

项目维护: Structure Analysis Team
