"""测试API端点"""
import pytest
from fastapi.testclient import TestClient
import tempfile
import os

from app.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestResultAPI:
    """测试结果解析API"""
    
    def test_root_endpoint(self, client):
        """测试根路径"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AI-Structure-FEA"
        assert data["status"] == "running"
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    @pytest.mark.legacy
    def test_get_supported_formats(self, client):
        """测试获取支持的格式 (RFC-001 §6.1 Bucket C: endpoint deleted with result_router)."""
        response = client.get("/api/v1/supported-formats")

        assert response.status_code == 200
        data = response.json()
        assert ".frd" in data["formats"]
        assert ".dat" in data["formats"]

    @pytest.mark.legacy
    def test_parse_result_file(self, client):
        """测试解析结果文件 (RFC-001 §6.1 Bucket C: endpoint deleted with result_parser)."""
        # 创建测试文件
        dat_content = b"""
displacement (m):
    1  0.001  0.002  0.000

stress (Pa):
    1  1.5e8  0.5e8  0.3e8  0.1e8  0.0  0.0
"""
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as f:
            f.write(dat_content)
            tmp_path = f.name
        
        try:
            with open(tmp_path, 'rb') as f:
                response = client.post(
                    "/api/v1/parse-result",
                    files={"file": ("test.dat", f, "application/octet-stream")}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            # file_name是临时文件名,检查扩展名即可
            assert data["file_name"].endswith(".dat")
            assert data["node_count"] > 0
        finally:
            os.unlink(tmp_path)
    
    @pytest.mark.legacy
    def test_parse_unsupported_format(self, client):
        """测试不支持的格式 (RFC-001 §6.1 Bucket C: endpoint deleted with result_router)."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test")
            tmp_path = f.name
        
        try:
            with open(tmp_path, 'rb') as f:
                response = client.post(
                    "/api/v1/parse-result",
                    files={"file": ("test.txt", f, "text/plain")}
                )
            
            assert response.status_code == 400
        finally:
            os.unlink(tmp_path)


class TestNLAPI:
    """测试自然语言解析API"""
    
    def test_get_supported_intents(self, client):
        """测试获取支持的意图"""
        response = client.get("/api/v1/supported-intents")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["intents"]) == 6
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
    def test_parse_natural_language(self, client):
        """测试解析自然语言"""
        response = client.post(
            "/api/v1/parse-nl",
            json={
                "text": "显示von Mises应力云图",
                "context": {}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["intent"] == "visualize"
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
    def test_parse_batch(self, client):
        """测试批量解析"""
        response = client.post(
            "/api/v1/parse-nl/batch",
            json=[
                "显示应力云图",
                "提取最大位移"
            ]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(item["success"] for item in data)
