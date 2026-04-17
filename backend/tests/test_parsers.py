"""测试结果解析器和自然语言解析器"""
import pytest
import tempfile
import os
from pathlib import Path

from app.parsers.result_parser import ResultParser
from app.parsers.nl_parser import NLParser, IntentType


class TestResultParser:
    """测试结果解析器"""
    
    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return ResultParser()
    
    def test_parse_nonexistent_file(self, parser):
        """测试解析不存在的文件"""
        result = parser.parse("/nonexistent/file.frd")
        
        assert result.success is False
        assert "文件不存在" in result.error_message
    
    def test_parse_unsupported_format(self, parser):
        """测试解析不支持的格式"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            tmp_path = f.name
        
        try:
            result = parser.parse(tmp_path)
            
            assert result.success is False
            assert "不支持的格式" in result.error_message
        finally:
            os.unlink(tmp_path)
    
    def test_parse_dat_file(self, parser):
        """测试解析.dat文本格式"""
        # 创建模拟.dat文件
        dat_content = """
displacement (m):
    1  0.001  0.002  0.000
    2  0.0015 0.0025 0.000
    3  0.002  0.003  0.000

stress (Pa):
    1  1.5e8  0.5e8  0.3e8  0.1e8  0.0  0.0
    2  1.8e8  0.6e8  0.4e8  0.2e8  0.0  0.0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix=".dat", delete=False) as f:
            f.write(dat_content)
            tmp_path = f.name
        
        try:
            result = parser.parse(tmp_path)
            
            assert result.success is True
            assert result.node_count > 0
            assert result.displacement is not None
            assert result.stress is not None
        finally:
            os.unlink(tmp_path)
    
    def test_compute_von_mises(self, parser):
        """测试von Mises应力计算"""
        result_data = {
            "stress": {
                "values": [
                    {
                        "node_id": 1,
                        "sxx": 100e6,
                        "syy": 50e6,
                        "szz": 30e6,
                        "sxy": 10e6,
                        "syz": 0,
                        "szx": 0
                    }
                ]
            }
        }
        
        derived = parser._compute_derived(result_data)
        
        assert derived["max_von_mises"] is not None
        assert derived["max_von_mises"] > 0


class TestNLParser:
    """测试自然语言解析器"""
    
    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        # 注意: 需要设置OPENAI_API_KEY环境变量
        return NLParser()
    
    def test_parse_visualize_intent(self, parser):
        """测试可视化意图解析"""
        # 跳过如果没有API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")
        
        result = parser.parse("显示von Mises应力云图")
        
        assert result.success is True
        assert result.intent == IntentType.VISUALIZE
        assert "von_mises" in result.target_fields or "stress" in result.target_fields
    
    def test_parse_extract_intent(self, parser):
        """测试提取意图解析"""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")
        
        result = parser.parse("提取最大应力位置")
        
        assert result.success is True
        assert result.intent == IntentType.EXTRACT
        assert result.confidence > 0.5
    
    def test_parse_verify_intent(self, parser):
        """测试验证意图解析"""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")
        
        result = parser.parse("检查最大应力是否超过屈服强度")
        
        assert result.success is True
        assert result.intent == IntentType.VERIFY
    
    def test_get_supported_intents(self, parser):
        """测试获取支持的意图列表"""
        intents = parser.get_supported_intents()
        
        assert "visualize" in intents
        assert "extract" in intents
        assert "compare" in intents
        assert "verify" in intents
        assert "report" in intents
        assert "query" in intents


class TestIntegration:
    """集成测试"""
    
    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        # 1. 解析结果文件
        parser = ResultParser()
        
        # 创建测试文件
        dat_content = """
displacement (m):
    1  0.001  0.002  0.000

stress (Pa):
    1  1.5e8  0.5e8  0.3e8  0.1e8  0.0  0.0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix=".dat", delete=False) as f:
            f.write(dat_content)
            tmp_path = f.name
        
        try:
            result = parser.parse(tmp_path)
            
            assert result.success is True
            assert result.max_displacement is not None
            assert result.max_von_mises is not None
        finally:
            os.unlink(tmp_path)
