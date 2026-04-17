.PHONY: install test run clean docs

# 安装依赖
install:
	cd backend && pip install -r requirements.txt

# 运行测试
test:
	cd backend && pytest tests/ -v --cov=app

# 启动API服务
run:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 清理
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete

# 生成文档
docs:
	cd backend && pdoc --html app --output-dir docs

# 格式化代码
format:
	cd backend && black app tests
	cd backend && isort app tests

# 类型检查
lint:
	cd backend && mypy app
