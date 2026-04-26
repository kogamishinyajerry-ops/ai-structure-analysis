"""报告生成服务 - 结构分析结果自动摘要与对比
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ..parsers.frd_parser import FRDParseResult
from .rule_engine import get_rule_engine
# RFC-001 §6.1 Bucket B: services.knowledge_base frozen — Sprint 2 RAG is not in
# the MVP wedge. Standards-citation linkage stays wired through the frozen
# module until M5/M6 rebuild (see backend/app/_frozen/sprint2/README.md).
from .._frozen.sprint2.knowledge_base import get_fea_knowledge_base

logger = logging.getLogger(__name__)

@dataclass
class ReportContent:
    summary: str
    metrics: Dict[str, Any]
    validation: Dict[str, Any]
    markdown: str
    increments: List[Dict[str, Any]] = field(default_factory=list)

class ReportGenerator:
    """报告生成器
    
    分析FEA结果,提取关键指标,并与理论值(如有)进行对比
    """
    
    YIELD_LIMIT_STEEL = 235.0  # MPa (Q235)

    def __init__(self, golden_samples_root: Optional[Path] = None):
        if golden_samples_root is None:
            # 默认路径
            self.gs_root = Path(__file__).parent.parent.parent.parent / "golden_samples"
        else:
            self.gs_root = golden_samples_root

    def generate(self, result: FRDParseResult, case_id: Optional[str] = None) -> ReportContent:
        """生成分析报告
        
        Args:
            result: FRD解析结果
            case_id: 黄金样本ID(可选)
            
        Returns:
            报告内容对象
        """
        # 1. 提取基础指标
        max_disp = result.max_displacement
        if max_disp is None and result.increments:
            max_disp = max((inc.max_displacement for inc in result.increments), default=0.0)
        max_disp = max_disp or 0.0

        max_vm = result.max_von_mises
        if max_vm is None and result.increments:
            max_vm = max((inc.max_von_mises for inc in result.increments), default=0.0)
        max_vm = max_vm or 0.0
        
        # 2. 计算安全系数 (简单线性模型)
        sf = self.YIELD_LIMIT_STEEL / max_vm if max_vm > 0 else float('inf')
        
        metrics = {
            "max_displacement": max_disp,
            "max_von_mises": max_vm,
            "safety_factor": round(sf, 2),
            "status": "SAFE" if sf > 1.5 else ("CRITICAL" if sf > 1.0 else "FAIL")
        }

        # 2b. 提取模态/屈曲指标
        increments_md = ""
        if result.increments:
            is_modal = any(inc.type == 'vibration' for inc in result.increments)
            is_buckling = any(inc.type == 'buckling' for inc in result.increments)
            
            if is_modal:
                freqs = [inc.value for inc in result.increments if inc.type == 'vibration']
                metrics["modal_frequencies"] = freqs
                increments_md += "\n### 振型与频率分析\n| 阶数 | 频率 (Hz) | 最大位移 |\n| :--- | :--- | :--- |\n"
                for inc in result.increments:
                    if inc.type == 'vibration':
                        increments_md += f"| {inc.index} | {inc.value:.3f} | {inc.max_displacement:.4f} |\n"
            
            if is_buckling:
                factors = [inc.value for inc in result.increments if inc.type == 'buckling']
                metrics["buckling_factors"] = factors
                increments_md += "\n### 屈曲稳定性分析\n| 阶数 | 载荷系数 (λ) | 稳定性判定 |\n| :--- | :--- | :--- |\n"
                for inc in result.increments:
                    if inc.type == 'buckling':
                        status = "Stable" if inc.value > 1.0 else "Unstable"
                        increments_md += f"| {inc.index} | {inc.value:.4f} | {status} |\n"
        
        # 3. 理论值对比 (如果是黄金样本)
        validation = {"status": "N/A", "error_percentage": 0.0}
        comparison_md = ""
        display_name = result.file_name
        
        if case_id:
            expected = self._load_expected_results(case_id)
            if expected:
                display_name = expected.get("case_name", result.file_name)
                
                # Try to find theoretical stress in various possible locations
                theory_vm = 0.0
                
                # 1. Standard path (GS-001)
                theory_vm = expected.get("correct_theoretical_calculation", {}).get("stress", {}).get("result_MPa", 0.0)
                
                # 2. Alternative path (GS-002 Truss)
                if theory_vm == 0:
                    theory_vm = abs(expected.get("theoretical_solutions", {}).get("stresses", {}).get("all_members", {}).get("value", 0.0))
                
                # 3. Alternative path (GS-003 Plane Stress)
                if theory_vm == 0:
                    theory_vm = expected.get("theoretical_solutions", {}).get("max_stress", {}).get("value", 0.0)
                
                if theory_vm > 0:
                    err = abs(max_vm - theory_vm) / theory_vm * 100
                    validation["status"] = "PASS" if err < 15 else "FAIL" # Slightly wider tolerance for complex models
                    validation["error_percentage"] = round(err, 2)
                    comparison_md = f"\n### 理论对标 (理论值: {theory_vm:.2f} MPa)\n- 相对误差: {validation['error_percentage']}%\n- 判定: {validation['status']}"

        # 4. 生成Markdown叙述
        markdown = f"""# 结构分析报告: {display_name}

## 核心指标摘要
- **最大位移**: {max_disp:.4f} (单位视模型而定)
- **最大等效应力 (von Mises)**: {max_vm:.2f} MPa
- **估算安全系数**: {metrics['safety_factor']} ({metrics['status']})
{comparison_md}
{increments_md}

## 结论
该结构在当前载荷工况下表现为 **{metrics['status']}**。
"""
        if validation["status"] == "FAIL":
            markdown += "\n> [!CAUTION]\n> 检测到FEA结果与理论解存在明显偏差，请检查网格收敛性或单元类型设置。"

        # 5. 规范合规性审计 (Phase 3 Sprint 7)
        rule_engine = get_rule_engine()
        fea_kb = get_fea_knowledge_base()
        
        audit_results = rule_engine.audit(metrics, standard_id="GB50017")
        if audit_results:
            markdown += "\n## 工程规范合规性审计 (GB50017)\n"
            for res in audit_results:
                status_icon = "✅" if res.status == "PASS" else ("⚠️" if res.status == "CRITICAL" else "❌")
                markdown += f"- {status_icon} **{res.rule_id}**: {res.description}\n"
                markdown += f"  - 限值: {res.limit} | 实测: {res.actual}\n"
                markdown += f"  - 依据: {res.citation}\n"
                
                # 如果失败，从知识库检索背景知识
                if res.status != "PASS":
                    kb_results = fea_kb.query(res.description, top_k=1)
                    if kb_results:
                        markdown += f"  - > [!NOTE]\n  - > **知识库参考**: {kb_results[0].content}\n"

        return ReportContent(
            summary=f"最大应力 {max_vm:.2f} MPa, 安全系数 {metrics['safety_factor']}",
            metrics=metrics,
            validation=validation,
            markdown=markdown,
            increments=[{
                "index": inc.index,
                "step": inc.step,
                "type": inc.type,
                "value": inc.value,
                "max_displacement": inc.max_displacement,
                "max_von_mises": inc.max_von_mises
            } for inc in result.increments]
        )

    def _load_expected_results(self, case_id: str) -> Optional[Dict[str, Any]]:
        """加载黄金样本预期结果"""
        path = self.gs_root / case_id / "expected_results.json"
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载预期结果失败 {case_id}: {e}")
        return None
