"""
桁架结构理论解计算脚本
Truss Structure Theoretical Solution Calculator

案例: 简单桁架 - 3杆件，三角形构型，集中载荷作用于顶点
验证FEA结果与静力学解析解

桁架结构:
```
         Node 3 (apex, P = 1000 N downward)
        / \
       /   \
      /     \
Node 1       Node 2
(fixed)     (roller)
```

静定桁架分析方法:
1. 求解支座反力 (平衡方程)
2. 求解各杆件轴力 (节点法或截面法)
3. 计算节点位移 (力-位移关系)

理论公式:
- 支座反力: R = P/2 (对称结构)
- 轴力: F = P / (2 * sin(θ))，θ为杆件与水平面夹角
- 位移: δ = F * L / (E * A)
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class TrussNode:
    """桁架节点"""
    id: int
    x: float
    y: float
    z: float = 0.0
    support_type: str = "free"  # "free", "fixed", "roller_x", "roller_y"
    fx: float = 0.0  # X方向力
    fy: float = 0.0  # Y方向力


@dataclass
class TrussMember:
    """桁架杆件"""
    id: int
    node_i: int
    node_j: int
    area: float  # 横截面积 A
    youngs_modulus: float  # 弹性模量 E
    length: float = 0.0
    angle: float = 0.0  # 与水平面夹角 (度)
    axial_force: float = 0.0  # 轴力 (拉为正，压为负)
    stress: float = 0.0  # 轴向应力
    deformation: float = 0.0  # 变形量


@dataclass
class TrussResults:
    """桁架分析结果"""
    reactions: Dict[str, float]  # 支座反力
    members: List[TrussMember]  # 各杆件信息
    displacements: Dict[int, Dict[str, float]]  # 节点位移 {node_id: {ux, uy}}
    max_displacement: float  # 最大节点位移
    max_axial_force: float  # 最大轴力


def create_truss(nodes: List[TrussNode], members: List[TrussMember]) -> None:
    """计算杆件几何属性"""
    for member in members:
        ni = next(n for n in nodes if n.id == member.node_i)
        nj = next(n for n in nodes if n.id == member.node_j)

        # 计算长度
        dx = nj.x - ni.x
        dy = nj.y - ni.y
        dz = nj.z - ni.z
        member.length = np.sqrt(dx**2 + dy**2 + dz**2)

        # 计算与水平面夹角
        member.angle = np.degrees(np.arctan2(dy, dx))


def analyze_truss_static(nodes: List[TrussNode], members: List[TrussMember],
                        load: Tuple[int, str, float]) -> Dict[str, float]:
    """
    桁架静力学分析 - 求解支座反力

    方法: 平衡方程
    - ΣFx = 0
    - ΣFy = 0
    - ΣM = 0 (about any point)

    参数:
        nodes: 节点列表
        members: 杆件列表
        load: (node_id, direction, magnitude)

    返回:
        reactions: 支座反力字典
    """
    node_id, direction, magnitude = load

    # 统计约束
    fixed_nodes = [n for n in nodes if n.support_type == "fixed"]
    roller_nodes = [n for n in nodes if "roller" in n.support_type]

    # 对于此桁架结构:
    # - Node 1: 固定支座 (Rx1, Ry1)
    # - Node 2: 滚动支座 (Ry2 only, 允许水平位移)

    # 平衡方程:
    # ΣFy = 0: Ry1 + Ry2 + P = 0 (P is negative, downward)
    # ΣM about node 1 = 0: Ry2 * L_base + P * (L_base/2) = 0
    # where P is the load at node 3

    # 获取几何参数
    node1 = next(n for n in nodes if n.id == 1)
    node2 = next(n for n in nodes if n.id == 2)
    L_base = node2.x - node1.x

    # 假设node 2是y方向的滚动支座（只约束y方向）
    # 从力矩平衡求Ry2:
    # ΣM_about_1 = 0: -P * (L_base/2) + Ry2 * L_base = 0
    # Ry2 = P * (L_base/2) / L_base = P/2 (向上为正)

    # P是向下的负值，所以:
    P = magnitude  # 应该是负值 (例如 -1000)
    Ry2 = -P / 2  # 向上

    # ΣFy = 0: Ry1 + Ry2 + P = 0
    Ry1 = -P - Ry2  # 向上

    # ΣFx = 0: Rx1 + Rx2 = 0
    # 但node 2是y方向滚动，Rx2 = 0 (允许水平位移)
    # 所以 Rx1 = 0

    reactions = {
        "node1_Rx": 0.0,
        "node1_Ry": Ry1,
        "node2_Ry": Ry2
    }

    return reactions


def calculate_axial_forces(nodes: List[TrussNode], members: List[TrussMember],
                           reactions: Dict[str, float], load: Tuple[int, str, float]) -> None:
    """
    计算各杆件轴力 - 使用节点法

    参数:
        members: 杆件列表 (会被修改)
        reactions: 支座反力
        load: 外载荷
    """
    node_id, direction, magnitude = load

    # 构建节点字典便于查找
    node_dict = {n.id: n for n in nodes}

    for member in members:
        ni = node_dict[member.node_i]
        nj = node_dict[member.node_j]

        # 计算杆件方向余弦
        dx = nj.x - ni.x
        dy = nj.y - ni.y
        L = member.length

        cos_alpha = dx / L  # x方向余弦
        cos_beta = dy / L   # y方向余弦

        # 对于桁架杆件，轴力在节点处分解为:
        # Fx = F * cos(alpha)
        # Fy = F * cos(beta)

        # 节点分析法:
        # 对于此简单桁架，我们可以直接计算:
        # Member 3 (1-2): 由于node 2是y方向滚动，member 3只受轴向力
        # Member 1 (1-3): 斜杆
        # Member 2 (2-3): 斜杆

        # 根据对称性:
        # - 两个斜杆长度相同，角度相反(+60°和-60°)
        # - 两个斜杆轴力大小相同

        # P = 1000 N downward at node 3
        P = abs(magnitude)  # 1000

        # 垂直方向平衡:
        # Node 3: F1*sin(60°) + F2*sin(60°) = P (向下)
        # 由于对称: 2 * F * sin(60°) = P
        # F = P / (2 * sin(60°)) = P / (2 * 0.866) = P / 1.732

        sin_60 = np.sin(np.radians(60))
        F_axial = P / (2 * sin_60)

        member.axial_force = F_axial  # 压为负？取决于约定

        # 对于此结构，两个斜杆都受压
        member.axial_force = -F_axial  # 压为负

        # 计算应力
        member.stress = member.axial_force / member.area

        # 计算变形
        # δ = F * L / (E * A)
        member.deformation = member.axial_force * member.length / (member.youngs_modulus * member.area)


def calculate_displacements(nodes: List[TrussNode], members: List[TrussMember],
                           reactions: Dict[str, float]) -> Dict[int, Dict[str, float]]:
    """
    计算节点位移

    方法: 能量法或直接刚度法
    对于简单桁架，使用能量法:
    δ = Σ(F * L) / (E * A)

    返回:
        displacements: {node_id: {ux, uy}}
    """
    # 获取材料参数 (假设所有杆件相同)
    E = members[0].youngs_modulus

    # 对于节点位移，需要考虑几何关系
    # 简化分析：计算各节点的等效位移

    # 计算每根杆件的应变能
    # 节点位移与杆件伸长量相关

    # 对于此对称桁架，位移可近似为:
    # - node 3的垂直位移 = δ = P * L³ / (E * A * some_factor)

    # 精确计算使用刚度矩阵法
    # 这里使用简化的能量法

    # 计算等效刚度
    # Node 3的垂直位移:

    # 从力的角度:
    # P作用下的垂直位移 δ_v = P * L_effect / (E * A_effect)

    # 对于两根斜杆并联:
    # 垂直位移 δ = (P/2) * L / (E * A * sin(60°))
    #            = P * L / (2 * E * A * sin(60°))

    # 获取参数
    node3 = next(n for n in nodes if n.id == 3)
    member1 = next(m for m in members if m.id == 1)

    P = abs(reactions["node2_Ry"]) * 2  # 总载荷
    L = member1.length
    A = member1.area

    sin_60 = np.sin(np.radians(60))

    # Node 3垂直位移
    delta_v = (P / 2) * L / (E * A * sin_60**2)  # 考虑几何非线性

    # 简化计算:
    delta_v_simple = P * L / (2 * E * A * sin_60)

    # 对于弹性小变形，使用线性近似
    # 实际上由于桁架是大变形小应变，需要用更精确的公式

    # 简化能量法:
    # δ_v = Σ(∂U/∂P) = Σ(F_i * ∂F_i/∂P * L_i/(E*A_i))

    # 更简单的理解：使用虚功法
    # δ_v = Σ(F_internal * F_virtual * L) / (E * A)

    # 对于单位载荷法:
    # δ = Σ(F * F_unit * L) / (E * A)

    # 内部力F是由P产生的轴力
    # 单位虚拟力F_unit是在目标点沿目标方向的单位力

    # Node 3垂直位移:
    # 只需要考虑斜杆的贡献

    # F = -P / (2 * sin(60°)) = -577.35 N (压力)
    # F_unit = 1/(2*sin(60°)) = 0.577 (单位力产生的轴力)

    F_internal = -P / (2 * sin_60)
    F_unit = 1 / (2 * sin_60)

    delta_v = (F_internal * F_unit * L) / (E * A)

    displacements = {
        1: {"ux": 0.0, "uy": 0.0},  # 固定端
        2: {"ux": 0.0, "uy": 0.0},  # 滚动端 (简化，水平位移忽略)
        3: {"ux": 0.0, "uy": delta_v}  # 顶点位移
    }

    return displacements


def print_report(nodes: List[TrussNode], members: List[TrussMember],
                reactions: Dict[str, float], displacements: Dict[int, Dict[str, float]]):
    """打印完整分析报告"""

    print("=" * 70)
    print("桁架结构理论解分析报告")
    print("Truss Structure Theoretical Analysis Report")
    print("=" * 70)

    print("\n【结构参数】")
    print(f"  节点数: {len(nodes)}")
    print(f"  杆件数: {len(members)}")
    print(f"  结构类型: 静定桁架 (三角形构型)")

    print("\n【节点坐标】")
    for node in nodes:
        print(f"  节点{node.id}: ({node.x}, {node.y}, {node.z}) - {node.support_type}")

    print("\n【杆件属性】")
    for member in members:
        print(f"  杆件{member.id}: 节点{member.node_i} → 节点{member.node_j}")
        print(f"    长度 L = {member.length:.4f} m")
        print(f"    截面面积 A = {member.area:.4f} m²")
        print(f"    角度 θ = {member.angle:.2f}°")

    print("\n【载荷条件】")
    print(f"  节点3: Py = -1000 N (向下)")

    print("\n【支座反力】")
    print(f"  节点1 (固定): Rx = {reactions['node1_Rx']:.4f} N, Ry = {reactions['node1_Ry']:.4f} N")
    print(f"  节点2 (滚动): Ry = {reactions['node2_Ry']:.4f} N")

    print("\n【轴力与应力】")
    for member in members:
        force_type = "压力" if member.axial_force < 0 else "拉力"
        print(f"  杆件{member.id}:")
        print(f"    轴力 F = {abs(member.axial_force):.4f} N ({force_type})")
        print(f"    应力 σ = {member.stress:.6f} MPa")

    print("\n【节点位移】")
    max_disp = 0
    max_node = 0
    for node_id, disp in displacements.items():
        ux = disp["ux"] * 1000  # mm
        uy = disp["uy"] * 1000
        print(f"  节点{node_id}: UX = {ux:.6f} mm, UY = {uy:.6f} mm")
        if abs(disp["uy"]) > abs(max_disp):
            max_disp = disp["uy"]
            max_node = node_id

    print(f"\n  最大位移: 节点{max_node}, UY = {max_disp*1000:.6f} mm")

    print("\n【理论公式验证】")
    print("  对于等边三角形桁架 (θ = 60°):")
    print("  - 支座反力: R1y = R2y = P/2 = 500 N")
    print("  - 杆件轴力: F = P/(2×sin60°) = 1000/(2×0.866) = 577.35 N (压力)")
    print("  - 垂直位移: δ = PL/(2×E×A×sin²60°)")

    print("\n" + "=" * 70)


def main():
    """主函数"""

    # ========== 定义桁架结构 ==========

    # 节点定义
    nodes = [
        TrussNode(id=1, x=0.0, y=0.0, z=0.0, support_type="fixed"),
        TrussNode(id=2, x=10.0, y=0.0, z=0.0, support_type="roller_y"),  # y方向滚动
        TrussNode(id=3, x=5.0, y=8.66025404, z=0.0, support_type="free"),  # 顶点
    ]

    # 杆件定义
    # 注意：CalculiX中T3D2单元的截面定义是 *SECTION, TYPE=TRUSS, A, t
    # 其中A是面积，t是厚度（可选）
    members = [
        TrussMember(id=1, node_i=1, node_j=3, area=10.0, youngs_modulus=210e9),
        TrussMember(id=2, node_i=2, node_j=3, area=10.0, youngs_modulus=210e9),
        TrussMember(id=3, node_i=1, node_j=2, area=10.0, youngs_modulus=210e9),
    ]

    # 外载荷
    load = (3, "fy", -1000.0)  # 节点3, Y方向, -1000N

    # ========== 计算几何属性 ==========
    create_truss(nodes, members)

    # ========== 静力学分析 ==========
    reactions = analyze_truss_static(nodes, members, load)

    # ========== 计算轴力 ==========
    calculate_axial_forces(nodes, members, reactions, load)

    # ========== 计算位移 ==========
    displacements = calculate_displacements(nodes, members, reactions)

    # ========== 输出报告 ==========
    print_report(nodes, members, reactions, displacements)

    # ========== 返回结果 ==========
    return {
        "nodes": nodes,
        "members": members,
        "reactions": reactions,
        "displacements": displacements
    }


if __name__ == "__main__":
    results = main()
