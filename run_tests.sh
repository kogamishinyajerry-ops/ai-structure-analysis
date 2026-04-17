#!/bin/bash
# Sprint 1 快速测试脚本

echo "========================================="
echo "AI-Structure-FEA Sprint 1 测试"
echo "========================================="
echo ""

# 切换到backend目录
cd backend || exit 1

echo "📦 1. 安装依赖..."
pip install -q -r requirements.txt

echo ""
echo "🧪 2. 运行单元测试..."
pytest tests/ -v --tb=short

echo ""
echo "📊 3. 生成测试覆盖率报告..."
pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

echo ""
echo "✅ 4. 测试完成!"
echo ""
echo "查看详细覆盖率报告: backend/htmlcov/index.html"
echo ""
echo "========================================="
echo "Sprint 1 核心功能验证完成"
echo "========================================="
