import pytest
from app.services.rule_engine import get_rule_engine
from app.services.report_generator import ReportGenerator

def test_rule_engine_audit():
    """测试规则引擎的基础审计功能"""
    engine = get_rule_engine()
    
    # 模拟一个超过 Q235 (215MPa) 的结果
    metrics = {
        "max_von_mises": 250.0,
        "max_displacement": 2.0
    }
    
    results = engine.audit(metrics, standard_id="GB50017", material="Q235")
    
    # 应包含强度校核
    strength_result = next(r for r in results if r.rule_id == "STRENGTH_01")
    assert strength_result.status == "FAIL"
    assert strength_result.limit == 215.0
    
    # 模拟一个符合要求的结果
    metrics_pass = {"max_von_mises": 150.0, "max_displacement": 1.0}
    results_pass = engine.audit(metrics_pass, standard_id="GB50017")
    assert all(r.status == "PASS" for r in results_pass)

def test_rule_engine_eurocode():
    """测试 Eurocode 3 规则逻辑"""
    engine = get_rule_engine()
    metrics = {"max_von_mises": 200.0}
    
    # Eurocode 3 S235 limit = 235 / 1.1 = 213.6
    results = engine.audit(metrics, standard_id="EUROCODE_3", material="S235")
    assert results[0].status == "PASS"
    assert results[0].limit == 213.64

def test_knowledge_base_linkage():
    """测试知识库联动逻辑 (逻辑层)"""
    from app.services.knowledge_base import get_fea_knowledge_base
    from app.services.report_generator import ReportGenerator
    from app.parsers.frd_parser import FRDParseResult
    
    gen = ReportGenerator()
    res = FRDParseResult(
        success=True,
        file_name="test.frd",
        file_size=1024,
        parse_time=0.1,
        max_von_mises=300.0, # 明显失败
        max_displacement=1.0,
        nodes={},
        elements={},
        displacements={},
        stresses={}
    )
    
    report = gen.generate(res)
    # 检查 Markdown 是否包含知识库参考
    assert "## 工程规范合规性审计" in report.markdown
    assert "知识库参考" in report.markdown
