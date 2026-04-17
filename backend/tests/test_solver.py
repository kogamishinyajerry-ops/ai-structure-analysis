import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import asyncio
from unittest.mock import MagicMock, patch

from app.main import app
from app.services.solver import get_solver_service

client = TestClient(app)

@pytest.fixture
def solver_service():
    return get_solver_service()

def test_solver_run_router():
    """测试启动求解器的API路由"""
    # 模拟一个存在的 .inp 文件
    with patch("pathlib.Path.exists", return_value=True):
        response = client.post(
            "/api/v1/solver/run",
            json={"case_id": "GS-001"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "PENDING"

def test_solver_status_router():
    """测试查询状态的API路由"""
    # 先注入一个模拟任务
    solver = get_solver_service()
    job_id = "test-job-123"
    from app.services.solver import SolverJob
    solver.jobs[job_id] = SolverJob(job_id, "test_case", Path("/tmp"))
    solver.jobs[job_id].status = "RUNNING"
    
    response = client.get(f"/api/v1/solver/status/{job_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "RUNNING"

@pytest.mark.asyncio
async def test_solver_execution_logic():
    """模拟求解器执行逻辑"""
    solver = get_solver_service()
    from app.services.solver import SolverJob
    job_id = "async-test-job"
    job = SolverJob(job_id, "test", Path("/tmp"))
    solver.jobs[job_id] = job  # Register the job
    
    # 模拟异步执行并在 job.logs 中添加内容
    job.status = "RUNNING"
    job.logs.append("Step 1: Initiation")
    job.logs.append("Step 2: Solving...")
    job.status = "COMPLETED"
    
    status = solver.get_job_status(job_id)
    assert status["status"] == "COMPLETED"
    assert "Step 2: Solving..." in status["logs"]
