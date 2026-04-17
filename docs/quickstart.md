# AI-Structure-FEA 快速开始指南

## 🚀 5分钟快速体验

### 前置要求

- Python 3.10+
- (可选) OpenAI API Key - 用于自然语言解析

### 安装步骤

```bash
# 1. 进入项目目录
cd "/Users/Zhuanz/20260408 AI StructureAnalysis"

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
cd backend
pip install -r requirements.txt

# 4. 配置环境变量(可选)
cp .env.example .env
# 编辑.env文件,设置OPENAI_API_KEY
```

### 运行测试

```bash
# 在backend目录下
pytest tests/ -v
```

### 启动API服务

```bash
# 在backend目录下
uvicorn app.main:app --reload
```

访问:
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

---

## 📝 使用示例

### 1. 解析结果文件

**使用curl**:

```bash
# 创建测试文件
cat > test.dat << EOF
displacement (m):
    1  0.001  0.002  0.000
    2  0.0015 0.0025 0.000

stress (Pa):
    1  1.5e8  0.5e8  0.3e8  0.1e8  0.0  0.0
    2  1.8e8  0.6e8  0.4e8  0.2e8  0.0  0.0
EOF

# 上传解析
curl -X POST "http://localhost:8000/api/v1/parse-result" \
  -H "accept: application/json" \
  -F "file=@test.dat"
```

**使用Python**:

```python
import requests

# 上传文件
with open('test.dat', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/parse-result',
        files={'file': f}
    )

result = response.json()
print(f"最大位移: {result['max_displacement']} m")
print(f"最大应力: {result['max_von_mises']} Pa")
```

### 2. 自然语言解析(需要API Key)

**使用curl**:

```bash
curl -X POST "http://localhost:8000/api/v1/parse-nl" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "显示von Mises应力云图",
    "context": {}
  }'
```

**使用Python**:

```python
import requests

response = requests.post(
    'http://localhost:8000/api/v1/parse-nl',
    json={
        'text': '提取最大应力位置',
        'context': {}
    }
)

result = response.json()
print(f"意图: {result['intent']}")
print(f"置信度: {result['confidence']}")
print(f"参数: {result['parameters']}")
```

---

## 🧪 使用黄金样本测试

```bash
# 运行GS-001验证
cd backend
pytest tests/test_golden_samples.py -v
```

---

## 📚 API端点列表

### 结果解析

- `POST /api/v1/parse-result` - 解析CalculiX结果文件
- `GET /api/v1/supported-formats` - 获取支持的文件格式

### 自然语言

- `POST /api/v1/parse-nl` - 解析自然语言指令
- `POST /api/v1/parse-nl/batch` - 批量解析
- `GET /api/v1/supported-intents` - 获取支持的意图类型

### 系统

- `GET /` - 根路径
- `GET /health` - 健康检查

---

## 🔧 配置说明

### 环境变量

创建`.env`文件:

```bash
# API配置
APP_NAME=AI-Structure-FEA
APP_VERSION=0.1.0
DEBUG=False

# OpenAI配置(必需,用于NLP功能)
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview

# 文件上传配置
MAX_UPLOAD_SIZE=104857600  # 100MB
```

---

## 📖 文档

- [项目README](../README.md)
- [Sprint 1报告](./sprint1_report.md)
- [Benchmark报告](./benchmark_report.md)
- [GS-001案例](../golden_samples/GS-001/README.md)

---

## 🐛 常见问题

### Q: pytest报错找不到模块?

A: 确保在backend目录下运行,且已激活虚拟环境:

```bash
cd backend
source ../venv/bin/activate
pytest tests/
```

### Q: NLP测试被跳过?

A: 需要设置`OPENAI_API_KEY`环境变量:

```bash
export OPENAI_API_KEY="your-key-here"
pytest tests/
```

### Q: 启动服务报错?

A: 检查依赖是否安装完整:

```bash
pip install -r requirements.txt
```

---

## 📞 支持

遇到问题?
- 查看[文档](../docs/)
- 运行测试验证环境: `pytest tests/ -v`
- 查看日志: 启动服务后查看控制台输出
