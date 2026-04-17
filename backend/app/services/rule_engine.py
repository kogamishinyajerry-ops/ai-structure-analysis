from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class ComplianceResult:
    standard: str
    rule_id: str
    description: str
    status: str  # PASS, FAIL, CRITICAL
    limit: float
    actual: float
    citation: str

class RuleEngine:
    """工程规范规则引擎
    
    自动校核计算结果是否符合特定行业标准 (GB50017, Eurocode 3 等)
    """

    # 预置标准限值 (简化版)
    STANDARDS = {
        "GB50017": {
            "name": "钢结构设计标准 (Chinese Standard)",
            "yield_stress": {
                "Q235": 215.0,  # f (MPa) 考虑安全系数分项系数
                "Q345": 310.0,
            },
            "partial_factor": 1.0  # GB50017 通常在 f 值中已包含
        },
        "EUROCODE_3": {
            "name": "Design of steel structures (European Standard)",
            "yield_stress": {
                "S235": 235.0,  # fy (MPa)
                "S355": 355.0,
            },
            "gamma_m0": 1.1  # 部分安全系数
        }
    }

    def audit(self, metrics: Dict[str, Any], standard_id: str = "GB50017", material: str = "Q235") -> List[ComplianceResult]:
        """执行合规性审计"""
        results = []
        
        if standard_id not in self.STANDARDS:
            return []

        std_config = self.STANDARDS[standard_id]
        
        # 1. 强度校核 (Strength Check)
        if "max_von_mises" in metrics:
            actual_stress = metrics["max_von_mises"]
            
            if standard_id == "GB50017":
                limit = std_config["yield_stress"].get(material, 215.0)
                description = f"强度校核: 最大等效应力应小于抗拉强度设计值 f ({material})"
            else: # EUROCODE_3
                fy = std_config["yield_stress"].get(material, 235.0)
                gamma = std_config["gamma_m0"]
                limit = fy / gamma
                description = f"Strength Check: σ_max < fy/γ_M0 (Standard: {material})"

            status = "PASS" if actual_stress < limit else ("CRITICAL" if actual_stress < limit * 1.1 else "FAIL")
            
            results.append(ComplianceResult(
                standard=standard_id,
                rule_id="STRENGTH_01",
                description=description,
                status=status,
                limit=round(limit, 2),
                actual=round(actual_stress, 2),
                citation=f"{standard_id} Section 6.2.1"
            ))

        # 2. 刚度/位移校核 (Stiffness Check - Simplified L/250)
        # 注意: 这里的 limit 是硬编码的示例，实际应根据跨度计算
        if "max_displacement" in metrics:
            results.append(ComplianceResult(
                standard=standard_id,
                rule_id="STIFFNESS_01",
                description="刚度校核: 最大挠度控制",
                status="PASS" if metrics["max_displacement"] < 5.0 else "FAIL",
                limit=5.0,
                actual=round(metrics["max_displacement"], 3),
                citation=f"{standard_id} Section 3.5"
            ))

        # 3. 模态校核 (Resonance Check)
        if "modal_frequencies" in metrics:
            freqs = metrics["modal_frequencies"]
            if freqs:
                f1 = freqs[0]
                critical_ranges = [(48, 52), (58, 62)] # 典型的 50Hz/60Hz 电机共振区
                is_resonance = any(low <= f1 <= high for low, high in critical_ranges)
                
                results.append(ComplianceResult(
                    standard=standard_id,
                    rule_id="DYNAMIC_01",
                    description="动力学共振校核: 避开常用电机转速频率 (50Hz/60Hz)",
                    status="FAIL" if is_resonance else "PASS",
                    limit=5.0, # 这里的 limit 语义较模糊，实际指避让间距
                    actual=round(f1, 2),
                    citation="ISO 10816 / GB/T 19886"
                ))

        # 4. 屈曲校核 (Stability Check)
        if "buckling_factors" in metrics:
            factors = metrics["buckling_factors"]
            if factors:
                lambda1 = factors[0]
                status = "PASS" if lambda1 > 3.0 else ("FAIL" if lambda1 < 1.0 else "CRITICAL")
                
                results.append(ComplianceResult(
                    standard=standard_id,
                    rule_id="STABILITY_01",
                    description="整体稳定性校核: 第一阶线性屈曲特征值 λ1",
                    status=status,
                    limit=3.0,
                    actual=round(lambda1, 3),
                    citation=f"{standard_id} Section 6.1"
                ))

        return results

# 单例
_rule_engine = None

def get_rule_engine():
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = RuleEngine()
    return _rule_engine
