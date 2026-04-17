"""
悬臂梁理论解计算脚本
Cantilever Beam Theoretical Solution Calculator

案例: 悬臂梁 - 一端固定，自由端集中力
验证FEA结果与理论计算

问题分析:
- 原始 expected_results.json 描述的是"简支梁"（Simply Supported Beam）
- 实际 FEA 案例是"悬臂梁"（Cantilever Beam）
- 两者理论公式完全不同

实际案例参数 (来自 cantilever_beam.inp):
- 几何: L=100m, 截面 10m×10m
- 材料: E=210 GPa, ν=0.3
- 载荷: P=400N (4节点各100N) 作用于自由端
- 边界: 左端固定 (节点1,12,23,34)

FEA结果 (来自 gs001_result.frd):
- 节点11 (自由端角点) 位移: UX=-36.87mm, UY=-493.56mm
- 节点1 (固定端角点) 应力: SXX=-190.08 MPa

理论解验证:
- 欧拉-伯努利梁理论给出 δ=0.00076mm, σ=0.24MPa
- FEA结果差异巨大，说明3D实体单元行为与理想梁理论不符
- 可能原因: 网格稀疏、深梁效应、载荷分布等
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class BeamProperties:
    """梁的几何和材料属性"""
    length: float          # 长度 L (m)
    width: float           # 截面宽度 b (m)
    height: float          # 截面高度 h (m)
    youngs_modulus: float # 弹性模量 E (Pa)
    poisson_ratio: float   # 泊松比 ν
    load: float            # 集中载荷 P (N)

    @property
    def area(self) -> float:
        """横截面积 A = b × h"""
        return self.width * self.height

    @property
    def moment_of_inertia(self) -> float:
        """截面惯性矩 I = bh³/12"""
        return self.width * self.height**3 / 12

    @property
    def section_modulus(self) -> float:
        """截面模量 Z = I/c = bh²/6"""
        return self.width * self.height**2 / 6

    @property
    def radius_of_gyration(self) -> float:
        """回转半径 r = √(I/A)"""
        return np.sqrt(self.moment_of_inertia / self.area)


@dataclass
class TheoreticalResults:
    """理论解结果"""
    max_deflection: float           # 最大挠度 δ_max (m)
    max_slope: float                # 最大转角 θ_max (rad)
    max_bending_moment: float       # 最大弯矩 M_max (N·m)
    max_bending_stress: float       # 最大弯曲应力 σ_max (Pa)
    max_shear_stress: float         # 最大剪应力 τ_max (Pa)
    shear_deformation_ratio: float # 剪切变形与弯曲变形之比


def euler_bernoulli_cantilever(props: BeamProperties) -> TheoreticalResults:
    """
    欧拉-伯努利梁理论 (纯弯曲理论，忽略剪切变形)

    适用范围: 细长梁 (L/h > 10)

    公式:
    - 最大弯矩: M_max = P × L
    - 最大应力: σ_max = M_max × c / I = P × L × (h/2) / I
    - 最大挠度: δ_max = P × L³ / (3 × E × I)
    """
    P = props.load
    L = props.length
    E = props.youngs_modulus
    G = E / (2 * (1 + props.poisson_ratio))
    I = props.moment_of_inertia
    A = props.area
    c = props.height / 2  # 中性轴到外层纤维距离

    # 弯矩
    max_bending_moment = P * L

    # 弯曲应力
    max_bending_stress = max_bending_moment * c / I

    # 纯弯曲挠度
    bending_deflection = P * L**3 / (3 * E * I)

    # 剪切变形 (Timoshenko修正)
    k_shear = 5 / 6  # 矩形截面剪切系数
    shear_deflection = P * L / (k_shear * A * G)
    shear_ratio = shear_deflection / bending_deflection

    # 总挠度 (Timoshenko)
    max_deflection = bending_deflection + shear_deflection

    # 最大剪应力 (矩形截面平均剪应力的1.5倍)
    max_shear_stress = 1.5 * P / A

    # 转角
    max_slope = P * L**2 / (2 * E * I)

    return TheoreticalResults(
        max_deflection=max_deflection,
        max_slope=max_slope,
        max_bending_moment=max_bending_moment,
        max_bending_stress=max_bending_stress,
        max_shear_stress=max_shear_stress,
        shear_deformation_ratio=shear_ratio
    )


def compare_with_fea(theory: TheoreticalResults,
                     fea_node11_disp: Tuple[float, float],
                     fea_node1_stress: float) -> Dict:
    """
    对比理论解与FEA结果
    """
    # FEA结果 (取绝对值进行比较)
    fea_uy = abs(fea_node11_disp[1])  # Y方向位移 (载荷方向)
    fea_ux = abs(fea_node11_disp[0])  # X方向位移
    fea_sxx = abs(fea_node1_stress)   # 弯曲应力

    # 理论值
    theory_uy = theory.max_deflection
    theory_sxx = theory.max_bending_stress

    return {
        "displacement_UY": {
            "theory_m": theory_uy,
            "fea_m": fea_uy,
            "diff_m": abs(theory_uy - fea_uy),
            "error_percent": abs(theory_uy - fea_uy) / theory_uy * 100 if theory_uy > 1e-12 else float('inf')
        },
        "displacement_UX": {
            "theory_m": 0.0,  # 纯弯曲无轴向位移
            "fea_m": fea_ux,
            "note": "UX来自泊松效应和深梁效应"
        },
        "stress_SXX": {
            "theory_Pa": theory_sxx,
            "fea_Pa": fea_sxx,
            "diff_Pa": abs(theory_sxx - fea_sxx),
            "error_percent": abs(theory_sxx - fea_sxx) / theory_sxx * 100 if theory_sxx > 1e-12 else float('inf')
        }
    }


def analyze_discrepancy(props: BeamProperties, theory: TheoreticalResults,
                       comparison: Dict, fea_node11_disp: Tuple[float, float]):
    """
    分析理论与FEA差异的原因
    """
    print("\n" + "=" * 70)
    print("差异分析 (Discrepancy Analysis)")
    print("=" * 70)

    # 1. 检查梁的细长比
    slenderness = props.length / props.height
    print(f"\n1. 几何分析:")
    print(f"   细长比 L/h = {slenderness:.2f}")
    if slenderness < 10:
        print(f"   → 深梁 (L/h < 10): 剪切变形和圣维南效应显著")
    elif slenderness < 20:
        print(f"   → 中等梁: 欧拉-伯努利理论误差约5-10%")
    else:
        print(f"   → 细长梁 (L/h > 20): 欧拉-伯努利理论适用")

    # 2. 检查剪切变形比例
    print(f"\n2. 变形分解:")
    print(f"   弯曲变形 δ_b = PL³/(3EI)")
    print(f"   剪切变形 δ_s = PL/(kAG)")
    print(f"   剪切/弯曲比 = {theory.shear_deformation_ratio:.4f}")
    if theory.shear_deformation_ratio > 0.1:
        print(f"   → 剪切变形显著 (>{theory.shear_deformation_ratio*100:.1f}%), Timoshenko理论更准确")
    else:
        print(f"   → 弯曲变形为主")

    # 3. 检查FEA UX位移
    fea_ux = abs(fea_node11_disp[0])
    fea_uy = abs(fea_node11_disp[1])
    ux_uy_ratio = fea_ux / fea_uy if fea_uy > 0 else 0
    print(f"\n3. 位移模式分析:")
    print(f"   UX/UY 比值 = {ux_uy_ratio:.4f}")
    print(f"   纯弯曲理论: UX ≈ 0 (因为载荷垂直于梁轴线)")
    print(f"   实际FEA: UX = {fea_ux*1000:.4f} mm (占UY的{ux_uy_ratio*100:.2f}%)")
    if ux_uy_ratio > 0.05:
        print(f"   → UX不可忽略，说明存在显著的泊松效应或深梁行为")

    # 4. 应力分析
    print(f"\n4. 应力分析:")
    stress_ratio = abs(comparison['stress_SXX']['fea_Pa']) / theory.max_bending_stress
    print(f"   FEA/理论 应力比 = {stress_ratio:.2f}")
    if 0.8 < stress_ratio < 1.2:
        print(f"   → 应力匹配良好 (误差<20%)")
    elif stress_ratio > 1.5:
        print(f"   → FEA应力显著高于理论，可能原因:")
        print(f"     * 网格过于粗糙导致应力集中")
        print(f"     * 载荷施加区域的奇异性")
        print(f"     * 固定端边界条件的影响")
    else:
        print(f"   → 应力差异较大，需要进一步调查")

    # 5. 总体评价
    print(f"\n5. 结论:")
    disp_error = comparison['displacement_UY']['error_percent']
    stress_error = comparison['stress_SXX']['error_percent']

    if disp_error > 1000 and stress_error > 100:
        print(f"   ⚠️ 理论与FEA存在巨大差异")
        print(f"   可能原因:")
        print(f"   a) FEA模型使用3D实体单元(C3D8)，与梁理论假设不同")
        print(f"   b) 载荷施加方式(4节点分布)与理论点载荷不同")
        print(f"   c) 固定端边界条件在3D模型中的实现方式")
        print(f"   d) 网格过于稀疏(仅10个单元)")
    else:
        print(f"   ✓ 理论与FEA结果基本一致")


def print_report(props: BeamProperties, theory: TheoreticalResults,
                comparison: Dict):
    """打印完整报告"""

    print("=" * 70)
    print("悬臂梁理论解计算报告")
    print("Cantilever Beam Theoretical Solution Report")
    print("=" * 70)

    print("\n【案例信息】")
    print("  本案例为悬臂梁分析 (Cantilever Beam)")
    print("  ⚠️ 注意: expected_results.json 中的简支梁理论值不适用于此案例!")

    print("\n【输入参数】")
    print(f"  几何参数:")
    print(f"    长度 L = {props.length} m")
    print(f"    截面尺寸 b × h = {props.width} × {props.height} m")
    print(f"    横截面积 A = {props.area:.4f} m²")
    print(f"    惯性矩 I = {props.moment_of_inertia:.4f} m⁴")
    print(f"    回转半径 r = {props.radius_of_gyration:.4f} m")
    print(f"\n  材料参数:")
    print(f"    弹性模量 E = {props.youngs_modulus:.4e} Pa = {props.youngs_modulus/1e9:.2f} GPa")
    print(f"    泊松比 ν = {props.poisson_ratio}")
    print(f"    剪切模量 G = {props.youngs_modulus/(2*(1+props.poisson_ratio))/1e9:.2f} GPa")
    print(f"\n  载荷:")
    print(f"    集中载荷 P = {props.load} N (自由端)")
    print(f"    载荷类型: 4节点分布 (各100N)")

    print("\n【欧拉-伯努利 + Timoshenko 梁理论解】")
    print(f"  最大弯矩 M_max = P×L = {theory.max_bending_moment:.4e} N·m")
    print(f"  最大弯曲应力 σ_max = M×c/I = {theory.max_bending_stress/1e6:.4f} MPa")
    print(f"  最大剪应力 τ_max = 1.5×P/A = {theory.max_shear_stress/1e6:.4f} MPa")
    print(f"\n  变形分析:")
    print(f"    弯曲变形 δ_b = PL³/(3EI) = {theory.max_deflection/(1+theory.shear_deformation_ratio)*1000:.4f} mm")
    print(f"    剪切变形 δ_s = PL/(kAG) = {theory.max_deflection*theory.shear_deformation_ratio/(1+theory.shear_deformation_ratio)*1000:.4f} mm")
    print(f"    剪切/弯曲比 = {theory.shear_deformation_ratio*100:.4f}%")
    print(f"    总挠度 δ_max = {theory.max_deflection*1000:.6f} mm")
    print(f"  最大转角 θ_max = {np.degrees(theory.max_slope):.6f}°")

    print("\n【FEA结果 (来自 gs001_result.frd)】")
    print(f"  节点11 (自由端角点, x=100, y=0, z=0):")
    print(f"    UX = {comparison['displacement_UX']['fea_m']*1000:.4f} mm")
    print(f"    UY = {comparison['displacement_UY']['fea_m']*1000:.4f} mm")
    print(f"  节点1 (固定端角点, x=0, y=0, z=0):")
    print(f"    SXX = {comparison['stress_SXX']['fea_Pa']/1e6:.4f} MPa")

    print("\n【理论 vs FEA 对比】")
    print(f"  UY (载荷方向位移):")
    print(f"    理论: {comparison['displacement_UY']['theory_m']*1000:.6f} mm")
    print(f"    FEA:  {comparison['displacement_UY']['fea_m']*1000:.4f} mm")
    print(f"    误差: {comparison['displacement_UY']['error_percent']:.2f}%")

    print(f"\n  SXX (固定端弯曲应力):")
    print(f"    理论: {comparison['stress_SXX']['theory_Pa']/1e6:.6f} MPa")
    print(f"    FEA:  {comparison['stress_SXX']['fea_Pa']/1e6:.4f} MPa")
    print(f"    误差: {comparison['stress_SXX']['error_percent']:.2f}%")

    # 打印差异分析
    analyze_discrepancy(props, theory, comparison,
                       (comparison['displacement_UX']['fea_m'],
                        comparison['displacement_UY']['fea_m']))

    print("\n" + "=" * 70)


def main():
    """主函数"""

    # ========== 实际案例参数 (来自 cantilever_beam.inp) ==========
    props = BeamProperties(
        length=100.0,           # L = 100 m
        width=10.0,              # b = 10 m
        height=10.0,             # h = 10 m
        youngs_modulus=210e9,    # E = 210 GPa
        poisson_ratio=0.3,       # ν = 0.3
        load=400.0               # P = 400 N (4×100N)
    )

    # ========== FEA结果 (来自 gs001_result.frd) ==========
    # 节点11: 自由端角点 (x=100, y=0, z=0)
    fea_node11_ux = -3.68729E-02  # m
    fea_node11_uy = -4.93560E-01  # m

    # 节点1: 固定端角点 (x=0, y=0, z=0)
    fea_node1_sxx = -1.90079E+08  # Pa

    # ========== 计算理论解 ==========
    theory = euler_bernoulli_cantilever(props)

    # ========== 对比分析 ==========
    comparison = compare_with_fea(
        theory,
        fea_node11_disp=(fea_node11_ux, fea_node11_uy),
        fea_node1_stress=fea_node1_sxx
    )

    # ========== 输出报告 ==========
    print_report(props, theory, comparison)

    # ========== 返回结果 ==========
    return {
        "properties": props,
        "theory": theory,
        "comparison": comparison,
        "fea_results": {
            "node11_displacement": {"UX": fea_node11_ux, "UY": fea_node11_uy},
            "node1_stress_SXX": fea_node1_sxx
        }
    }


if __name__ == "__main__":
    results = main()
