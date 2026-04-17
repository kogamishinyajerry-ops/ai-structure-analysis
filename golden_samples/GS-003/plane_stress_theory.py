"""
平面应力理论解计算脚本
Plane Stress Theoretical Solution Calculator

案例: 带孔平板单轴拉伸 - 应力集中分析
验证FEA结果与解析解

问题描述:
┌─────────────────────────────┐
│           ↑ σ_apply         │
│                             │
│      ┌─────────┐            │
│      │    ○    │  ← 圆孔    │
│      │  D=20   │            │
│      └─────────┘            │
│                             │
│           ↓ σ_apply         │
└─────────────────────────────┘

理论公式 (Inglis, 1913):
- 无限大板中椭圆孔的应力集中
- 对于圆形孔 (a=b=r): K_t = 3
- 对于有限宽板，需修正

Kirsch公式 (1898):
σ_max = σ_nom × (1 + 2×a/b)
其中 a=短半轴, b=长半轴 (对于圆形孔 a=b=r):
σ_max = 3 × σ_nom

Peterson公式 (考虑有限宽度):
K_t = 3 - 3.14×(d/W) + 3.66×(d/W)² - 1.53×(d/W)³
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class PlateParameters:
    """平板参数"""
    width: float           # 板宽 W (mm)
    height: float          # 板高 H (mm)
    thickness: float       # 板厚 t (mm)
    hole_diameter: float    # 孔径 D (mm)
    youngs_modulus: float  # 弹性模量 E (MPa)
    poisson_ratio: float    # 泊松比 ν
    applied_displacement: float  # 施加强制位移 (mm)


@dataclass
class TheoreticalResults:
    """理论解结果"""
    nominal_stress: float       # 名义应力 σ_nom (MPa)
    stress_concentration: float  # 应力集中系数 K_t
    max_stress: float          # 最大应力 σ_max (MPa)
    applied_force: float        # 等效载荷 P (N)
    strain: float              # 应变 ε


def calculate_kirsch_solution(params: PlateParameters) -> TheoreticalResults:
    """
    Kirsch公式 - 无限大板中圆形孔的应力集中

    公式: σ_max = σ_nom × (1 + 2×a/b)
    对于圆形孔 (a=b=r): K_t = 3

    适用于: d/W < 0.4 (孔径远小于板宽)
    """
    # 名义应力 = E × ε
    strain = params.applied_displacement / params.height
    sigma_nom = params.youngs_modulus * strain

    # Kirsch应力集中系数 (无限大板)
    K_t_kirsch = 3.0

    # 最大应力
    sigma_max = K_t_kirsch * sigma_nom

    # 等效载荷
    # P = σ × A_net = σ × (W - D) × t
    A_net = (params.width - params.hole_diameter) * params.thickness
    P = sigma_nom * A_net

    return TheoreticalResults(
        nominal_stress=sigma_nom,
        stress_concentration=K_t_kirsch,
        max_stress=sigma_max,
        applied_force=P,
        strain=strain
    )


def calculate_peterson_solution(params: PlateParameters) -> TheoreticalResults:
    """
    Peterson公式 - 考虑有限宽度修正的应力集中系数

    公式: K_t = 3 - 3.14×(d/W) + 3.66×(d/W)² - 1.53×(d/W)³

    适用于: 有限宽板，d/W < 0.6
    """
    # 名义应力
    strain = params.applied_displacement / params.height
    sigma_nom = params.youngs_modulus * strain

    # 直径宽度比
    d_W = params.hole_diameter / params.width

    # Peterson应力集中系数
    K_t = 3 - 3.14 * d_W + 3.66 * d_W**2 - 1.53 * d_W**3

    # 最大应力
    sigma_max = K_t * sigma_nom

    # 等效载荷
    A_net = (params.width - params.hole_diameter) * params.thickness
    P = sigma_nom * A_net

    return TheoreticalResults(
        nominal_stress=sigma_nom,
        stress_concentration=K_t,
        max_stress=sigma_max,
        applied_force=P,
        strain=strain
    )


def calculate_stress_field(params: PlateParameters) -> Dict[str, float]:
    """
    计算关键位置的应力场

    关键位置:
    1. 孔边A点 (θ=0°): σ_xx最大
    2. 孔边B点 (θ=90°): σ_yy最大
    3. 远场: σ_xx = σ_nom
    """
    strain = params.applied_displacement / params.height
    sigma_nom = params.youngs_modulus * strain
    K_t = 3.0  # 使用Kirsch值

    # 远场应力
    sigma_xx_infinity = sigma_nom
    sigma_yy_infinity = 0

    # A点 (θ=0°, x轴正方向孔边)
    # σ_θ = σ_nom × (1 + 2×a/b) - σ_nom × (1 + 2×a/b)×cos(2θ)
    # 在θ=0时: σ_θ = σ_nom × (1 + 2) = 3σ_nom
    sigma_A = K_t * sigma_nom

    # B点 (θ=90°, y轴正方向孔边)
    # 在θ=90°时: σ_θ = -σ_nom (压应力)
    sigma_B = -sigma_nom

    # C点 (θ=45°)
    sigma_C = sigma_nom  # 与远场相同

    return {
        "A_point_theta_0": sigma_A,    # σ_θ at θ=0°
        "B_point_theta_90": sigma_B,   # σ_θ at θ=90°
        "C_point_theta_45": sigma_C,  # σ_θ at θ=45°
        "far_field_xx": sigma_xx_infinity,
        "far_field_yy": sigma_yy_infinity
    }


def print_report(params: PlateParameters, kirsch: TheoreticalResults,
                peterson: TheoreticalResults, stress_field: Dict):
    """打印完整报告"""

    print("=" * 70)
    print("平面应力理论解分析报告")
    print("Plane Stress Theoretical Analysis Report")
    print("=" * 70)

    print("\n【平板参数】")
    print(f"  板宽 W = {params.width} mm")
    print(f"  板高 H = {params.height} mm")
    print(f"  板厚 t = {params.thickness} mm")
    print(f"  孔径 D = {params.hole_diameter} mm")
    print(f"  d/W = {params.hole_diameter/params.width:.4f}")
    print(f"\n  材料参数:")
    print(f"  弹性模量 E = {params.youngs_modulus} MPa")
    print(f"  泊松比 ν = {params.poisson_ratio}")
    print(f"\n  载荷:")
    print(f"  施加强制位移 Δ = {params.applied_displacement} mm")

    print("\n【应变与名义应力】")
    print(f"  应变 ε = Δ/H = {kirsch.strain:.6f}")
    print(f"  名义应力 σ_nom = E×ε = {kirsch.nominal_stress:.4f} MPa")

    print("\n【应力集中系数】")
    print(f"  Kirsch公式 (无限大板): K_t = {kirsch.stress_concentration:.4f}")
    print(f"  Peterson公式 (有限宽修正): K_t = {peterson.stress_concentration:.4f}")
    print(f"  修正系数 = {peterson.stress_concentration/kirsch.stress_concentration:.4f}")

    print("\n【最大应力预测】")
    print(f"  Kirsch: σ_max = {kirsch.max_stress:.4f} MPa")
    print(f"  Peterson: σ_max = {peterson.max_stress:.4f} MPa")

    print("\n【应力场分布】")
    print(f"  A点 (θ=0°, 孔边): σ = {stress_field['A_point_theta_0']:.4f} MPa (拉)")
    print(f"  B点 (θ=90°, 孔边): σ = {stress_field['B_point_theta_90']:.4f} MPa (压)")
    print(f"  C点 (θ=45°): σ = {stress_field['C_point_theta_45']:.4f} MPa")
    print(f"  远场: σ_xx = {stress_field['far_field_xx']:.4f} MPa")

    print("\n【等效载荷】")
    print(f"  P = σ_nom × A_net = {kirsch.applied_force:.4f} N")
    print(f"  A_net = (W-D)×t = ({params.width}-{params.hole_diameter})×{params.thickness} = {params.width-params.hole_diameter} mm²")

    print("\n【公式汇总】")
    print("  Kirsch公式: σ_max = σ_nom × (1 + 2×a/b)")
    print("              对于圆形孔: K_t = 3")
    print("")
    print("  Peterson公式: K_t = 3 - 3.14×(d/W) + 3.66×(d/W)² - 1.53×(d/W)³")
    print("               适用于有限宽板修正")

    print("\n" + "=" * 70)


def main():
    """主函数"""

    # ========== 平板参数 ==========
    params = PlateParameters(
        width=100.0,           # W = 100 mm
        height=200.0,          # H = 200 mm
        thickness=1.0,         # t = 1 mm
        hole_diameter=20.0,    # D = 20 mm
        youngs_modulus=210000.0,  # E = 210 GPa = 210000 MPa
        poisson_ratio=0.3,     # ν = 0.3
        applied_displacement=0.5  # Δ = 0.5 mm
    )

    # ========== 计算理论解 ==========
    kirsch = calculate_kirsch_solution(params)
    peterson = calculate_peterson_solution(params)
    stress_field = calculate_stress_field(params)

    # ========== 输出报告 ==========
    print_report(params, kirsch, peterson, stress_field)

    # ========== 返回结果 ==========
    return {
        "params": params,
        "kirsch": kirsch,
        "peterson": peterson,
        "stress_field": stress_field
    }


if __name__ == "__main__":
    results = main()
