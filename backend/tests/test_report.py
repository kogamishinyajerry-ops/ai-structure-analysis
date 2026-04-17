import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import os

from app.main import app

client = TestClient(app)

@pytest.fixture
def sample_frd():
    """获取GS-001的FRD文件路径"""
    return Path(__file__).parent.parent.parent / "golden_samples" / "GS-001" / "gs001_result.frd"

def test_generate_report_endpoint(sample_frd):
    """测试报告生成端点"""
    if not sample_frd.exists():
        pytest.skip("GS-001 FRD file not found")
        
    with open(sample_frd, "rb") as f:
        response = client.post(
            "/api/v1/report/generate",
            files={"file": ("gs001_result.frd", f, "application/octet-stream")},
            data={"case_id": "GS-001"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "metrics" in data
    assert "max_von_mises" in data["metrics"]
    assert "markdown" in data
    assert "悬臂梁" in data["markdown"]  # 应包含报告标题
    
    # 验证对标逻辑
    assert data["validation"]["status"] in ["PASS", "FAIL"]
    print(f"\nReport Generated: {data['summary']}")

def test_generate_report_no_file():
    """测试未上传文件的报错"""
    response = client.post("/api/v1/report/generate")
    assert response.status_code == 422 # FastAPI validation error
