# GS-003: 平面应力分析 - 带孔平板单轴拉伸

> **⚠️ Status: `insufficient_evidence`** — see [FP-003](../../docs/failure_patterns/FP-003-gs003-missing-hole-and-bc-direction.md) for the empirical attribution.
> Per ADR-011 §HF3 + Golden Rule #5 ("no GS → no test"), this case is **excluded from the regression lane** until the issues documented in FP-003 are resolved. Do not use this case as a validation benchmark.

---


## 案例概述

GS-003 是一个经典的平面应力问题案例——带孔平板在单轴拉伸下的应力集中分析。用于验证FEA对应力集中现象的捕捉能力。

## 问题描述

```
┌─────────────────────────────┐
│←── W = 100 mm ──→          │
│                             │
│    ┌─────────┐             │
│    │    ○    │  ↑ 强制位移  │
│    │ D=20mm  │  Δ=0.5mm   │
│    └─────────┘             │
│                             │
│                        ↓    │
└─────────────────────────────┘
     H = 200 mm
```

## 结构参数

### 几何尺寸

| 参数 | 符号 | 数值 | 单位 |
|------|------|------|------|
| 板宽 | W | 100 | mm |
| 板高 | H | 200 | mm |
| 板厚 | t | 1 | mm |
| 孔径 | D | 20 | mm |
| 直径宽度比 | d/W | 0.2 | - |

### 材料参数

- **材料**: STEEL
- **弹性模量**: E = 210 GPa
- **泊松比**: ν = 0.3

### 载荷条件

- **类型**: 强制位移
- **位置**: 顶部边缘 (y=H)
- **大小**: UX = 0.5 mm (水平拉伸)
- **边界**: 底部边缘全约束

## 理论解

### 应变与名义应力

```
应变: ε = Δ/H = 0.5/200 = 0.0025

名义应力: σ_nom = E × ε = 210000 × 0.0025 = 525 MPa
```

### 应力集中系数

**Kirsch公式 (无限大板)**:
```
K_t = 1 + 2×(a/b) = 1 + 2×1 = 3.0

其中 a = b = r (圆形孔)
```

**Peterson公式 (有限宽修正)**:
```
K_t = 3 - 3.14×(d/W) + 3.66×(d/W)² - 1.53×(d/W)³
    = 3 - 3.14×0.2 + 3.66×0.04 - 1.53×0.008
    = 3 - 0.628 + 0.1464 - 0.0122
    = 2.506
```

### 最大应力预测

```
σ_max = K_t × σ_nom = 2.506 × 525 = 1315.73 MPa
```

### 应力场分布

在极坐标下 (以孔心为原点):

```
σ_θ = σ_nom × [1 + K_t×cos(2θ)]/2 + ...

关键点:
- A点 (θ=0°): σ_max = 1315.73 MPa (拉应力)
- B点 (θ=90°): σ_min = -525 MPa (压应力)
- C点 (θ=45°): σ = 525 MPa
```

## 有限元模型

### 网格信息

- **单元类型**: CPS4R (4节点平面应力，缩减积分)
- **单元数**: 8
- **节点数**: 15
- **网格说明**: 粗网格简化模型

### 边界条件

- **底部** (y=0): UX=0, UY=0 (固定)
- **顶部** (y=H): UX=0.5 mm (施加强制位移)

## FEA结果（待生成）

运行CalculiX后，结果将保存在 `gs003_result.frd` 中。

预期结果：
- 孔边最大应力: ≈ 1315 MPa (允许较大误差，因粗网格)
- 远场应力: ≈ 525 MPa

## 验收标准

### 解析器验证

1. **FRD文件解析**
   - 验证能正确解析CPS4R单元
   - 验证能提取平面应力分量 (SXX, SYY, SZZ)

2. **应力值验证**
   - 远场应力与理论值误差 < 5%
   - 孔边应力集中现象可观察到

### 应力集中验证

```
K_t_FEA = σ_max_FEA / σ_nom

预期: 2.0 < K_t_FEA < 3.0
```

## 文件清单

### 输入文件

- `gs003.inp` - CalculiX输入文件
- `plane_stress_theory.py` - 理论解计算脚本

### 输出文件

- `gs003_result.frd` - CalculiX结果文件 (需运行求解器生成)

### 参考文件

- `expected_results.json` - 预期结果

## 使用方法

### 1. 运行CalculiX求解

```bash
cd golden_samples/GS-003
ccx gs003
```

### 2. 使用AI-Structure-FEA解析

```python
from backend.app.parsers.frd_parser import FRDParser

parser = FRDParser()
result = parser.parse("gs003_result.frd")

# 提取应力
for elem_id, elem_data in result.elements.items():
    print(f"单元{elem_id} SXX: {elem_data.stress['SXX']} MPa")
```

### 3. 运行理论解计算

```bash
python plane_stress_theory.py
```

### 4. 自动化验证

```bash
pytest tests/test_golden_samples.py::test_gs003 -v
```

## 注意事项

1. 本案例为经典应力集中问题
2. 粗网格会低估应力集中峰值（网格奇异性）
3. 细网格结果应更接近Peterson公式预测值
4. 适用于验证FEA的应力集中捕捉能力

## 更新历史

- 2026-04-09: 创建GS-003平面应力案例
