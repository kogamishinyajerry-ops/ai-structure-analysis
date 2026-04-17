"""Pytest配置文件"""
import pytest
import os


def pytest_configure(config):
    """配置pytest"""
    # 设置环境变量(用于测试)
    os.environ.setdefault("OPENAI_API_KEY", "test-key-for-pytest")
    os.environ.setdefault("DEBUG", "True")


def pytest_collection_modifyitems(config, items):
    """修改测试项"""
    # 为需要API key的测试添加标记
    for item in items:
        if "skipif" in item.keywords:
            # 检查是否是因为缺少API key而跳过
            for marker in item.iter_markers(name="skipif"):
                if "OPENAI_API_KEY" in str(marker.args):
                    item.add_marker(pytest.mark.integration)
