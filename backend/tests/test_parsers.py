"""NL parser tests.

RFC-001 §6.1 Bucket C: TestResultParser + TestIntegration removed along
with backend/app/parsers/result_parser.py. The .frd code path was a
perpetual-empty stub and the .dat regex never matched real CalculiX output.
The replacement is the Layer-1 CalculiX adapter built in W2 (RFC §4.5).
"""
import os

import pytest

from app.parsers.nl_parser import IntentType, NLParser


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
