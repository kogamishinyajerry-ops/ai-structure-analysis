.PHONY: install test run clean docs docker-base docker-probe hot-smoke cold-smoke

# ---------- Legacy backend helpers ----------

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

# ---------- P1-01 containerized toolchain (ADR-008) ----------

IMAGE ?= ghcr.io/kogamishinyajerry-ops/ai-fea-engine
TAG   ?= p1-base
LOCAL_IMAGE ?= ai-fea-engine:$(TAG)

# Build the P1-01 base image locally (CalculiX 2.21 + FreeCAD 0.22 + gmsh).
docker-base:
	docker build -t $(LOCAL_IMAGE) .

# Run the toolchain probes against the locally built image.
docker-probe: docker-base
	docker run --rm -e AI_FEA_IN_CONTAINER=1 $(LOCAL_IMAGE) \
		pytest tests/test_toolchain_probes.py -v --tb=short

# Hot smoke: real ccx + FreeCAD + gmsh inside the container. This is the
# P1-02 Demo Gate entrypoint; it is wired up in P1-02 and currently just
# runs the test lane so the target exists for downstream phases to extend.
hot-smoke: docker-base
	docker run --rm -e AI_FEA_IN_CONTAINER=1 $(LOCAL_IMAGE) \
		pytest tests/ -v --tb=short -k "hot_smoke or toolchain_probes"

# Cold smoke: graph-wiring regression only (no container required).
cold-smoke:
	pytest tests/test_cold_smoke_e2e.py -v --tb=short
