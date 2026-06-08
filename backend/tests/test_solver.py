from pathlib import Path
from unittest.mock import patch

import pytest
from app.main import app
from app.services.solver import get_solver_service
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture
def solver_service():
    return get_solver_service()


def test_solver_run_router():
    """A valid non-signed case_id launches a job (200, status RUNNING — the route records the
    SimulationJob as RUNNING and returns immediately; the ccx subprocess runs in the background)."""
    # 模拟一个存在的 .inp 文件
    with patch("pathlib.Path.exists", return_value=True):
        response = client.post("/api/v1/solver/run", json={"case_id": "demo-candidate"})
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "RUNNING"


def test_solver_run_refuses_signed_registry():
    """Round-2 audit C2: solver-run WRITES ccx outputs into gs_root/<case_id>, so a
    ^GS-\\d{3}$ id must be refused 422 (sealed golden samples are read-only, ADR-011 §HF1.7a)."""
    with patch("pathlib.Path.exists", return_value=True):
        response = client.post("/api/v1/solver/run", json={"case_id": "GS-001"})
    assert response.status_code == 422
    assert "signed-registry" in response.json()["detail"]


def test_solver_run_rejects_malformed_case_id():
    """Round-2 audit C2: a traversal/malformed case_id is rejected 400 before any filesystem
    access (the case_id is interpolated into gs_root/<case_id>)."""
    response = client.post("/api/v1/solver/run", json={"case_id": "../../etc/passwd"})
    assert response.status_code == 400


def test_solver_run_inp_path_into_signed_registry_refused():
    """Round-2 audit C1: a client inp_path resolving through a sealed GS-NNN dir is refused 422
    (ccx would otherwise write outputs into the sealed deck's directory)."""
    with patch("pathlib.Path.exists", return_value=True):
        response = client.post(
            "/api/v1/solver/run",
            json={"case_id": "demo-candidate", "inp_path": "golden_samples/GS-001/gs001.inp"},
        )
    assert response.status_code == 422
    assert "signed-registry" in response.json()["detail"]


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
