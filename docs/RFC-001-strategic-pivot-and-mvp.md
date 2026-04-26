# RFC-001: AI-Structure-FEA 战略转向与 MVP 重构方案

| 字段 | 值 |
|---|---|
| 文档编号 | RFC-001 |
| 标题 | 战略转向与 MVP 重构方案 |
| 状态 | **FROZEN（已冻结，作为项目核心指南）** |
| 版本 | v1.0 |
| 起草日期 | 2026-04-26 |
| 冻结日期 | 2026-04-26 |
| 适用范围 | 全项目（含产品、技术、GTM、运营） |
| 修订规则 | 任何对本文档的修改必须通过 RFC-002+ 流程，不得直接编辑本文 |

---

## 0. 摘要（Executive Summary）

AI-Structure-FEA 项目从 Sprint 1+2 的"广度铺开"模式转向**单点穿透模式**。冻结战略三选项：

1. **长期定位**：跨求解器 Copilot（不绑定 ANSYS/Abaqus/CalculiX 任一），目标对标 "Cursor for CAE"
2. **GTM 路径**：PLG 自下而上，从设计院项目骨干工程师起步
3. **覆盖范围（长期）**：仿真前处理 + 后处理 + 报告撰写全流程

冻结 MVP wedge：**面向化工/电力设计院的"设备基础/结构件静力强度评定报告 Copilot"**。Desktop-first（Electron + 本地 Python 后端），单工程师 30 分钟产出可签字交付的 Word 报告。

冻结 6 周技术地基重铸 + 90 天种子用户行军：

- 技术：抽象 ResultReader 层、Electron 壳、4 个 solver adapter（CalculiX/ANSYS 优先）、本地 Python runtime、Aliyun LLM 代理
- 用户：5 个种子设计院工程师，3 个月内产生 5 份签字提交的真实报告

冻结 5 个非功能纪律：

- Evidence over eloquence：所有 AI 输出必须挂载证据 ID
- Tools over reasoning：LLM 不接触数字，所有数值由确定性代码计算
- Observable by default：每个 AI 决策可追溯到原始数据
- Slow is fast，narrow is wide：先做对一件事再做多件事
- Founder-led ground truth：种子用户访谈、微信群支持、现场陪伴不可委托

---

## 1. 战略定位

### 1.1 长期愿景（24–36 个月）

成为 CAE 领域的"Copilot 层"——位于求解器（ANSYS / Abaqus / CalculiX / Nastran / LS-DYNA）和工程师之间，把工程师从"操作员"升级为"决策者"。靠生态广度赢，而非求解器深度。

参考标杆：GitHub Copilot 之于 IDE，Cursor 之于代码编辑器。

**明确不做**：自研求解器、替代主流求解器的前处理 GUI、做一个新的"国产 ANSYS"。

### 1.2 切入路径

切入点选在"求解器之后"的工作环节，因为：

- 前处理（建模、网格、边界条件）AI 介入风险高、错误后果严重
- 求解器是 30 年算法积累的硬骨头，不是 AI 优势区
- 后处理 + 报告是工程师 60–70% 时间消耗、认知负荷低、模板化程度高的环节

### 1.3 三大战略选择（已冻结）

**选择 1：长期定位 = 跨求解器 Copilot**。架构上从 Day-1 假设多 solver，CalculiX 是首发实现，但 ResultReader 抽象层必须支持 .rst / .odb / .op2 的扩展。

**选择 2：GTM = PLG 自下而上**。第一批付费用户为设计院 30–38 岁项目骨干工程师，自费/项目组级别预算（不走信息中心采购）。

**选择 3：长期覆盖范围 = 全流程**。但这是 24 个月愿景，**不是 6 个月交付目标**。MVP 只做报告生成；后处理探索 M4 启动；前处理副驾 M13+ 启动。

### 1.4 商业价值优先级

| 价值维度 | 权重 | 说明 |
|---|---|---|
| 合规与可审计性 | 最高 | EvidenceBundle 是产品核心，规范行业（化工/电力/核电）的进场钥匙 |
| 知识资产化 | 高 | 沉淀公司私有工程经验，老工程师退休不带走 |
| 标准化与流程合规 | 中高 | 报告模板强制化，质量管理部门预算线 |
| 节省时间 | 副产品 | 不作为主要价值主张去讲（所有竞品都讲） |

定价远期方向：按"项目数 / 报告数 / 受监管资产数"收费，**不做 per-seat 定价**。

---

## 2. MVP 边界定义

### 2.1 Wedge 内的 Wedge

第一个 MVP 只做**一类报告**：

> **基于有限元结果的"设备基础 / 结构件静力强度评定报告"**

锁定理由：
- 频率最高（每个工业项目几十到几百份）
- 物理最简（线弹性静力分析）
- 模板最收敛（全国设计院差异 < 30%）
- 风险最低（结果易检查、规范判据简单）
- 替换效益最高（信息密度低、重复性高）

### 2.2 功能边界（DO）

按 5 步用户旅程组织。任何超出此清单的功能在 MVP sprint 计划中**一律不准排入**。

#### 步骤 1：新建项目（Project Wizard）
固定 8 字段：
1. 项目名称
2. 工程编号
3. 计算对象
4. 设计依据规范（GB / ASME / Eurocode 三选一）
5. 设计单位
6. 工程师姓名
7. 审核人姓名
8. 计算日期

#### 步骤 2：导入仿真结果
- CalculiX `.frd` + `.dat`：完整支持
- ANSYS `.rst`：只读支持（位移、Mises 应力、坐标、单元拓扑）
- Abaqus `.odb`：通过 helper 脚本转 HDF5 后导入（仅占位 stub，M4 完整实现）
- Nastran `.op2`：只读支持（pyNastran 包装）
- 网格文件 `.inp` / `.cdb` / `.bdf`：可选，用于"模型概况"章节

#### 步骤 3：选择模板
内置 3 个模板：
- 通用 FEA 静力强度评定报告
- 设备基础计算书
- 简单结构构件计算书

模板格式：`.docx` + 配套 YAML 配置（描述章节顺序与占位符白名单）。**MVP 必须支持"上传客户自有模板覆盖内置"**。

#### 步骤 4：自动生成草稿

**确定性生成器**（Python 直接计算，不经过 LLM）：
- 模型概况（节点数、单元数、单元类型分布、网格尺寸）
- 材料属性表
- 边界条件汇总
- 关键结果数值（最大位移、最大 Mises 应力、最大主应力、安全系数）
- 4 张标准图（网格图、边界条件示意图、Mises 应力云图、变形图）
- 结果一致性自检

**LLM 生成器**（受约束的文本生成）：
- 工程概述（2–3 句，基于步骤 1 元数据 + 模型概况）
- 结果解读（强约束：必须引用具体数值 + 必须说明位置）
- 工程结论（固定句式模板，LLM 只填变量值）
- 建议（仅当 SF < 1.5 或 σ_max 超阈值时触发）

#### 步骤 5：审阅 + 编辑 + 导出
- docx 预览
- 原地编辑 LLM 段落
- 每段"重新生成"按钮（可附 prompt 微调）
- 替换图片（用工程师自己用 ParaView 出的图）
- 调整数值四舍五入位数
- 导出 `.docx`（必须）+ `.pdf`（可选）

### 2.3 非功能边界（DON'T）

以下功能在 MVP 阶段**绝对不做**，违反此清单的 PR 一律驳回：

| 不做的功能 | 原因 |
|---|---|
| 交互式对话/Chat 界面 | Wizard 流程 > Chat 流程，设计院工程师不知该问什么 |
| 知识库 RAG | 模板里硬编码规范引用即可，RAG 留到 M4 |
| 3D 交互可视化 | PyVista 出 4 张固定 PNG 即可 |
| 任何前处理功能 | 不读、不改、不验证 .inp 输入文件 |
| 非线性 / 动力 / 热 / 多物理场 | MVP 只支持线弹性静力 |
| 规范自动校核 | 引用条款可，自动判合规不可（法律责任问题） |
| 云端 / 协作 / 多用户 | Desktop 应用、本地数据、单工程师 |
| 移动端 / Web App | 仅 Electron 桌面 |
| 求解器调用 | 不发起计算，只读结果 |
| LLM 算数 | 数值由确定性代码算，LLM 只措辞 |
| AI 审核工程师写的内容 | 一旦 AI 介入审稿就侵入工程师责任边界 |

### 2.4 AI 行为边界（信任地基的 5 条规则）

**规则 1**：LLM 输出必须挂载证据 ID。每段文字背后有证据 bundle（用了哪些数值、来自哪个字段、计算的哪个变量）。证据不出现在 docx 里，但内部 `.json` sidecar 存档。

**规则 2**：模板占位符是白名单制。LLM 不能填的字段，prompt 里都不暴露。

**规则 3**：定型化句式优先于自由生成。"工程结论"段落用固定模板，LLM 只填变量值 + 选择 conclusion phrase。

**规则 4**：低置信度必须显式 flag。LLM 不确定时输出 `[需工程师确认]` 标记，导出 docx 高亮显示，工程师须显式删除标记才能定稿。

**规则 5**：所有导出 docx 末尾标注"AI 辅助生成 + 工程师 X 审阅确认"。

### 2.5 质量基线（5 条硬指标，任一不达标不上线）

| 指标 | 目标 |
|---|---|
| 30 分钟测试 | 未培训工程师从首次启动到导出第一份愿意签字的报告 ≤ 30 分钟 |
| 数值准确率 | 100%（所有报告中数值与原始结果文件交叉验证误差为零） |
| 文本可接受率 | ≥ 70%（AI 生成段落工程师改动比例 ≤ 30%） |
| 模板符合度 | 100%（生成 docx 与设计院模板格式完全一致） |
| 种子签字率 | ≥ 80%（5 种子用户产出的报告 ≥ 80% 实际签字提交） |

### 2.6 预留接口（MVP 不实现但要为它留位置）

- **ResultReader 抽象层**：Day-1 按多 solver 设计接口（详见第 4 章）
- **TemplateEngine 抽象层**：3 内置模板 + 用户上传走同一引擎
- **EvidenceBundle 持久化**：每份报告 `.json` sidecar，schema 在 MVP 阶段冻结
- **用户行为埋点**：本地遥测，第一版就要埋

---

## 3. 种子用户策略

### 3.1 用户画像（精确版）

> 30–38 岁、入院 5–10 年、**每周写 ≥2 份强度/静力计算书**、并且**过去半年内主动给同事推荐过至少 1 个非官方工具**的项目骨干工程师。

全国估计不到 1 万人，可一个一个找出来的规模。

### 3.2 行业聚焦（5 个种子用户分布）

**优先（强烈推荐）**：
- 化工 / 石化设计院（中石化系、中石油系、化工三院、赛鼎、天华化工）
- 电力 / 火电 / 核电设计院（电力设计院系列、华电系、中电工程系）

**理想分布**：5 个种子 = 3 个化工 + 2 个电力

**MVP 阶段不做**：
- 民用建筑设计院（动力分析为主，MVP 静力覆盖率不足）
- 桥梁设计院（动力 + 大变形为主）

### 3.3 找人渠道（按 ROI 排序）

**渠道 1（必做，预期 50% 候选）**：仿真秀（simwe.com）+ 知乎深度回答作者私信
**渠道 2（必做，预期 30% 候选）**：高校工科导师（Top 20 学科 30 位导师）邮件请求推荐毕业生
**渠道 3（补充）**：垂直微信群渗透（潜水 1 个月观察活跃用户）
**渠道 4（补充）**：设计院内部 KOL（公众号作者）反向接触
**渠道 5（最后再做）**：付费精准广告（第一年完全不做）

### 3.4 第一次接触（私信模板）

```
您好，我是 XX，看了您在 [具体帖子链接] 里写的关于 [具体技术点] 的分析，特别有启发。

我和几位同行（也是化工/电力设计院的工程师）在做一个开源工具：把 ANSYS / 
Abaqus / CalculiX 的计算结果文件直接转成"可签字的强度评定报告 docx"。
目标是把工程师写报告的时间从 4–8 小时压到 30 分钟。

还在 alpha 阶段，需要找 5 个真实在写报告的工程师做产品共建。如果方便，
想约您 30 分钟视频访谈，主要是听您聊 1）现在写一份典型的 [设备/基础] 
强度报告流程是什么，2）最痛的是哪几个环节。访谈费 ¥300（红包），
不卖东西、不需要承诺试用。

您方便的话回复时间即可。
```

预期回复率：5–15%。

### 3.5 访谈 7 个核心问题

1. 上周你具体写了几份报告？分别是什么？（验证频次画像）
2. 拿最近一份报告，能不能花 5 分钟讲一遍你从拿到任务到提交报告的全流程？（挖真实工作流）
3. 这份报告里，哪一段你觉得最浪费时间但又必须做？（挖痛点）
4. 你们院的报告模板是怎么管理的？（验证模板假设）
5. 计算结果文件你们用什么软件出？输出格式是什么？（验证 solver 占比）
6. 你最近一次"觉得这个工作可以被自动化"是什么时候？（挖工具开放度）
7. 你们院的电脑能装第三方软件吗？需要 IT 审批吗？（验证 PLG 假设）

访谈后 24 小时内：写 1 页 markdown 纪要，存进 `users/` 目录。

### 3.6 90 天行军图

| 阶段 | 时间 | 里程碑 |
|---|---|---|
| 候选漏斗搭建 | Week 1–2 | 30 个候选名单，发 30 条私信 |
| 访谈轮 1 | Week 3–4 | 完成 5–10 次访谈，筛 3 个 A 类种子 |
| Alpha 安装 | Week 5–6 | 2 个 A 类用户安装，**创始人现场陪同** |
| 第一份报告 | Week 7–8 | 2 用户产出"内部参考用"对照报告 |
| 迭代 + 第三种子 | Week 9–10 | 第 3 个 A 类用户接入 |
| **第一份签字报告** | Week 11–12 | ≥1 个种子签字提交真实项目报告（PMF 第一信号） |
| Day 90 复盘 | Day 90 | 5 种子全接入，≥2 份签字报告，每种子周产 ≥1 份草稿 |

90 天打不到底线 = 回头质疑 MVP 边界，而非加种子用户。

### 3.7 支持模型

- 创始人开 1 个微信群，5 个种子全在内
- 工作时间 30 分钟内、非工作时间 4 小时内响应
- 每周三 20:00 固定 office hour（创始人不可委托）
- 每月轮流去 1 个种子用户城市现场陪伴 1 天
- 5 个种子终身免费 Pro 版授权

### 3.8 健康度指标（只看这 3 个）

- 周产出签字报告数：M1 = 1，M3 = 5，M6 = 15
- 种子主动转介率：D90 时能给出具体人名
- 周活跃打开次数：≥ 3 次

**不看**：注册数、安装数、报告生成数、NPS、停留时长。

### 3.9 创始人不可委托的 3 件事

- 所有候选人初次访谈，创始人本人做（前 30 次必须）
- 5 人微信群创始人 24 小时盯着
- 每周日晚上写"种子用户周报"，**手写**

### 3.10 刻意不做的 4 件事

- 急着做 PR / 媒体曝光（前 6 个月不做）
- 参加大型行业会议（目标用户不在那）
- 做"内测申请表"机制（垃圾邮箱 99%）
- 5 种子打通前接受融资 pitch 邀请

---

## 4. 技术架构：跨求解器 ResultReader 抽象层

### 4.1 抽象层级（核心原则）

抽象的"原子" = **一个有具体物理意义、有明确空间归属、有明确单位的场量**。

不抽象成 `ResultFile`（太粗），不抽象成 `FieldArray`（太细）。

### 4.2 4 层架构

```
┌────────────────────────────────────┐
│ Layer 4: Application               │
│  报告生成器 / 模板引擎 / LLM 编排    │
└────────────────────────────────────┘
                ↓ 只依赖 Layer 3
┌────────────────────────────────────┐
│ Layer 3: Domain                    │
│  Mesh / Material / BC / Solution   │
│  + 派生量计算（vonMises 等）        │
│  + 单位换算 / 坐标系变换             │
└────────────────────────────────────┘
                ↑ 实现自 Layer 2 接口
┌────────────────────────────────────┐
│ Layer 2: ResultReader 接口契约      │
│  ReaderHandle 协议 + 规范字段名表   │
└────────────────────────────────────┘
                ↑ 各 solver 实现
┌────────────────────────────────────┐
│ Layer 1: Concrete Adapters         │
│  CalculiXReader / NastranReader /  │
│  AnsysReader / AbaqusReader        │
└────────────────────────────────────┘
```

**强约束**：
- Layer 4 永远不导入 Layer 1
- Layer 3 不解析文件
- Layer 2 不算派生量
- Layer 1 不外泄 solver 怪癖

### 4.3 核心类型定义（Layer 2 + Layer 3）

```python
class FieldLocation(Enum):
    NODE = "node"
    INTEGRATION_POINT = "ip"
    ELEMENT_CENTROID = "centroid"
    ELEMENT = "element"

class ComponentType(Enum):
    SCALAR = "scalar"
    VECTOR_3D = "vec3"
    TENSOR_SYM_3D = "tensor_sym3"  # 6 分量

class UnitSystem(Enum):
    SI = "SI"             # m, Pa, kg, N, s
    SI_MM = "SI_mm"       # mm, MPa, t, N, s（设计院最常用）
    ENGLISH = "English"   # in, psi, slug, lbf, s
    UNKNOWN = "unknown"   # 必须由用户在 wizard 显式选

@dataclass(frozen=True)
class Quantity:
    value: float | np.ndarray
    unit: str
    def to(self, unit: str) -> "Quantity": ...

class CanonicalField(Enum):
    DISPLACEMENT = "displacement"
    STRESS_TENSOR = "stress_tensor"
    STRAIN_TENSOR = "strain_tensor"
    REACTION_FORCE = "reaction_force"
    NODAL_COORDINATES = "node_coords"
    ELEMENT_VOLUME = "elem_volume"
    # 白名单：MVP 只 6 个；扩展走 RFC 流程

@dataclass
class FieldMetadata:
    name: CanonicalField
    location: FieldLocation
    component_type: ComponentType
    unit_system: UnitSystem
    source_solver: str
    source_field_name: str
    source_file: Path
    coordinate_system: str  # "global" | "local" | "nodal_local"
    was_averaged: bool | str  # True / False / "unknown"

class FieldData:
    """惰性加载：metadata 立刻可读，values() 才触发 IO"""
    metadata: FieldMetadata
    def values(self) -> np.ndarray: ...
    def at_nodes(self) -> np.ndarray: ...

@dataclass
class SolutionState:
    step_id: int
    step_name: str
    time: float | None
    load_factor: float | None
    available_fields: list[CanonicalField]

class ReaderHandle(Protocol):
    @property
    def mesh(self) -> "Mesh": ...
    @property
    def materials(self) -> dict[str, "Material"]: ...
    @property
    def boundary_conditions(self) -> list["BoundaryCondition"]: ...
    @property
    def solution_states(self) -> list[SolutionState]: ...
    def get_field(self, name: CanonicalField, step_id: int) -> FieldData | None: ...
    def close(self) -> None: ...
```

### 4.4 规范字段映射表

| CanonicalField | CalculiX (.frd) | ANSYS (.rst) | Abaqus (.odb) | Nastran (.op2) |
|---|---|---|---|---|
| DISPLACEMENT | DISP (NODE) | U (NODE) | U (NODE) | DISPLACEMENT |
| STRESS_TENSOR | STRESS (NODE,外推) | S (NODE,外推) | S (IP默认/外推) | STRESS |
| STRAIN_TENSOR | TOSTRAIN | EPEL | E (IP) | STRAIN |
| REACTION_FORCE | FORC | F (受约束节点) | RF | SPCFORCE |
| ELEMENT_VOLUME | 自算 | EVOL 或自算 | EVOL | 自算 |

### 4.5 各 Solver 处理策略

| Solver | 策略 | 工作量 |
|---|---|---|
| CalculiX | 自研，复用 Sprint 2 的 frd_parser | 1 周重构 + 2 周补二进制 |
| Nastran | **wrap pyNastran**（开源 BSD，10 年成熟） | 1 周 |
| ANSYS | **wrap ansys-mapdl-reader**（PyAnsys 出品，MIT） | 1 周 |
| Abaqus | **subprocess + helper 脚本**：用户在 Abaqus 环境跑 odb_export.py 转 HDF5，adapter 读 HDF5 | 1+1 周 |

MVP 优先级：CalculiX → ANSYS → Nastran → Abaqus（stub）。

### 4.6 6 个工程陷阱（设计时必须预先想到）

1. **坐标系污染**：ANSYS 局部坐标系下输出，FieldMetadata.coordinate_system 强制标注，domain 层统一转全局
2. **节点平均 vs 不平均**：FieldData 接口区分 `values()` 与 `values_per_element_at_node()`，max 计算用 unaveraged，云图用 averaged
3. **单元类型动物园**：HEX8/SOLID185/C3D8/CHEXA 同物异名，建立 CanonicalElementType 映射表
4. **节点 ID 不连续**：Mesh 类内部维护 `node_id_array`（原始 ID）+ `node_index`（连续 0..N-1），numpy 用 index，输出用 ID
5. **多 step 多 increment**：SolutionState 平铺所有 (step, increment) 组合，UI 显示为 "Step-1, t=1.0"
6. **单位制刺杀**：MVP 阶段必须在 wizard 强制用户选 SI / SI_mm / English，**永远不要 silently 假设**

### 4.7 合规测试方法（黄金样本套件）

```
golden_samples/
├── GS-001_simply_supported_beam/        # 已有
├── GS-002_thick_cylinder_internal_pressure/
├── GS-003_lifting_lug_strength/         # 设计院最常见
├── GS-004_pressure_vessel_local_stress/
└── GS-005_equipment_foundation_static/
```

每个 GS 包含 4 个 solver 的输入 + 结果 + 解析解。合规测试断言：
- 跨 solver 一致性容差：≤ 0.5%（max disp） / ≤ 1%（max stress）
- 与解析解差：≤ 5%

### 4.8 ADR（架构决策记录）

| ADR | 决策 | 理由 |
|---|---|---|
| ADR-001 | 派生量永远不在 Layer 1 算 | 跨 solver 一致性 |
| ADR-002 | CanonicalField 是闭集，扩展走 RFC | 抽象不发散 |
| ADR-003 | adapter 不做"启发式补全" | silent assumption 是头号杀手 |
| ADR-004 | adapter 不做缓存、不做 IO 优化 | 早期优化是腐烂源头 |
| ADR-005 | 加新 solver 必先加新 GS 黄金样本 | 一致性可证伪 |

---

## 5. 桌面应用架构：Electron + 本地 Python

### 5.1 选型决策（已冻结）

| 选项 | 决策 | 理由 |
|---|---|---|
| 桌面框架 | **Electron** | Python 集成成熟、auto-updater 工业级、社区大 |
| 前端 | **React + TypeScript + Vite** | 团队熟悉、Electron 标配 |
| 后端 | **Python 3.12 + FastAPI**（本地子进程） | 沿用 Sprint 1 资产 |
| 状态管理 | **Zustand** | 轻量、无样板代码 |
| 安装包 | **NSIS via electron-builder** | Windows 标准 |
| 自动更新 | **electron-updater + GitHub Releases + Aliyun OSS 镜像** | 工业级 |
| 崩溃报告 | **Sentry** | 免费层够早期用 |

**明确不选**：Tauri / Wails / Native Qt / PWA / React Native。

### 5.2 整体架构（3 进程解耦）

```
┌─────────────────────────────────────────┐
│ Electron Main Process (Node.js)         │
│ - 窗口 / 菜单 / 系统托盘                  │
│ - Python subprocess 监督                 │
│ - Auto-updater                          │
│ - 系统级文件对话框                        │
└─────────────────────────────────────────┘
       ↕ Electron IPC      ↕ subprocess + stdio
┌──────────────────┐  ┌──────────────────────┐
│ Renderer Process │  │ Python Backend       │
│ React + Chromium │←→│ FastAPI on 127.0.0.1 │
│                  │HTTP│ ResultReader 抽象层  │
│                  │   │ 报告生成 / LLM 编排   │
└──────────────────┘  └──────────────────────┘
                              ↕ HTTPS
                       ┌────────────────────┐
                       │ 你的云端 LLM 代理     │
                       │ (Aliyun 北京/杭州)   │
                       └────────────────────┘
```

进程职责严格切开：
- **Main**：只做系统级编排，不写业务
- **Renderer**：只做 UI + 状态，不直接读写文件
- **Python Backend**：所有业务逻辑（未来可平移到云端）

### 5.3 Python Runtime 打包（决策：Embedded CPython）

**淘汰**：PyInstaller（VTK 兼容差）、cx_Freeze、PyOxidizer（不成熟）、Conda-pack（体积巨大）

**选择**：官方 `python-3.12-embed-amd64.zip` + 自行 `pip install` 依赖。

```bash
# CI 打包流程
curl -O https://www.python.org/ftp/python/3.12.x/python-3.12.x-embed-amd64.zip
unzip -d python_runtime python-3.12.x-embed-amd64.zip
# 启用 site-packages
echo "Lib\\site-packages" >> python_runtime/python312._pth
echo "import site" >> python_runtime/python312._pth
# 装 pip + 依赖
python_runtime/python.exe get-pip.py
python_runtime/python.exe -m pip install -r requirements.lock \
    --target=python_runtime/Lib/site-packages
# 拷应用代码
cp -r backend/app python_runtime/app
# 清理
find python_runtime -name "__pycache__" -exec rm -rf {} +
find python_runtime -name "*.pyi" -delete
# electron-builder 作为 extraResources 打入
```

**预期体积**：未压缩 ~455MB，NSIS 压缩后 ~280MB。**500MB 是硬上限**。

### 5.4 IPC 协议（HTTP REST + WebSocket）

```python
# Python 后端启动
import secrets
port = find_free_port(49152, 65535)
host = "127.0.0.1"  # 强制 localhost
token = secrets.token_urlsafe(32)
print(f"READY {port} {token}", flush=True)

# 中间件
@app.middleware("http")
async def auth_middleware(request, call_next):
    if request.headers.get("X-Session-Token") != token:
        return Response(status_code=401)
    return await call_next(request)
```

```typescript
// Electron Main
const py = spawn(pythonPath, [backendEntry], { stdio: 'pipe' });
py.stdout.on('data', (chunk) => {
    const m = chunk.toString().match(/^READY (\d+) (\S+)$/);
    if (m) {
        global.backendPort = parseInt(m[1]);
        global.backendToken = m[2];
        mainWindow.webContents.send('backend-ready');
    }
});
```

**安全要点**：
- 绑 127.0.0.1（不是 0.0.0.0）
- 端口随机
- 每次启动新 token
- 子进程崩溃自动 retry 一次，二次失败提示用户

### 5.5 LLM 调用（中国设计院特殊性）

**架构**：
```
Electron App → 你的 Aliyun 代理 → [通义 Qwen-Max 主用] [智谱 GLM-4 备用] [百度 ERNIE 备用]
```

**为什么必须自建代理**：
- 不能在 Electron 客户端嵌入 API key（asar 不加密）
- 设计院内网常拦截 OpenAI 直连
- 央企对工程数据出境敏感
- 自建代理是商业模式钥匙（限速、计费、模型路由）

**用户身份**：邮箱 + device_token（90 天），免登录但可识别用量。

**透明度规则**（每次生成 AI 段落前 UI 弹窗）：
- 明确列出"会发送：项目元数据、关键数值、几何描述"
- 明确列出"不会发送：结果文件本身、节点级原始数据、内部命名"
- 用户点"继续生成"才发请求

**Pro 版企业方案（M9+）**：私有化 LLM 代理 Docker 镜像，部署到设计院内部 K8s。

### 5.6 自动更新策略

- **electron-updater + GitHub Releases**（CDN 在国内勉强可用）
- **Aliyun OSS 国内镜像**（主路径）
- 默认**不静默更新**，用户点"立即更新"才下载
- 双通道：stable（月度）/ beta（周更，给种子用户）
- 回滚能力：`%LOCALAPPDATA%\AI-Structure\old_versions\` 保留上一版本

### 5.7 遥测与隐私

**收集**（默认开启 + 显式披露）：
- 应用版本、OS 版本、CPU/内存型号
- 崩溃堆栈（**清洗后**：去文件路径、用户名、项目名）
- 功能使用计数
- 性能指标
- 错误类型（不含文件内容）

**绝不收集**：
- 任何文件内容
- 任何文件路径
- 数值结果
- 用户输入的文字
- 网络标识

**用户控制**：设置 → 隐私 → 一键禁用全部遥测。提供"查看遥测历史"按钮。

### 5.8 安装与首启体验

**Windows 优先（80% 用户）**：
- EV 代码签名证书（**必须**，否则 SmartScreen 拦截）
- 默认安装到 `%LOCALAPPDATA%\AI-Structure\`（不需管理员权限）
- 安装时间目标：< 90 秒
- 首启目标：< 5 秒

**首启流程**：
1. 启动屏（≤ 2 秒）
2. 欢迎页 + 工程师类型选择（化工/电力/其他）
3. 隐私通知 + EULA
4. 邮箱填写（用于免费 LLM 配额）
5. **直接进入"创建第一份报告"wizard，预填 GS-001 演示数据**
6. 30 秒看到第一份完整报告

### 5.9 反模式（写进 ADR，不准违反）

| 反模式 | 原因 |
|---|---|
| Electron Main 写业务逻辑 | Main 崩溃 = 整个应用崩溃 |
| Renderer 直接读写文件 | 跨平台时痛苦 |
| API key 嵌入客户端 | asar 不加密，5 分钟被解出来 |
| 早期追求多平台 | Windows 一个先做对 |
| React Native / Flutter 跨端 | 我们不需要手机端 |
| 自己写 auto-updater | electron-updater 是工业标准 |
| 早期做插件系统 | 安全模型 1 个月人力，对种子无用 |

---

## 6. 迁移路径：从 Sprint 2 现状到新架构

### 6.1 五桶分类

**桶 A：保留 + 立刻重构**
- `task_spec.py` / `report_spec.py` / `evidence_bundle.py`（Schema 瘦身 + 增强）
- `frd_parser.py`（重构成 CalculiXReader 实现 ReaderHandle）
- 测试基础设施

**桶 B：保留但冷藏**（移到 `_frozen/sprint2/`）
- `nl_parser.py`
- `services/knowledge_base.py`
- `services/visualization.py`（除"出 PNG"最小子集）
- `api/routes/knowledge.py`

**桶 C：直接废弃**
- `parsers/result_parser.py`（_parse_frd 是永远返回空的 stub；正则匹配 .dat 实际匹配不到任何真实文件）
- `api/result.py`

**桶 D：从零新建**
- `core/types/`（Layer 2/3 schema）
- `adapters/{calculix,ansys,nastran,abaqus}/`
- `domain/{stress_derivatives,units,coordinates}/`
- `services/report/`（template engine, draft generator, docx exporter）
- `electron/`（main, preload, python-supervisor, updater）
- `frontend/`（React/Vite + 5 核心页面）
- `proxy/`（Aliyun ECS LLM 代理）
- `golden_samples/GS-002` 至 `GS-005`

**桶 E：完全删除**
- `backend/venv/`（应在 .gitignore，被误 commit）
- `backend/.pytest_cache/`
- 任何 stub 占位文件

### 6.2 Schema 瘦身指令

**`evidence_bundle.py`** 增强：
- EvidenceItem 增加 `field_metadata: Optional[FieldMetadata]`
- EvidenceItem 增加 `derivation: Optional[List[str]]`（依赖的 evidence_id）
- `data` 改为 union type（SimulationEvidence / ReferenceEvidence / AnalyticalEvidence）
- `add_evidence` 加唯一性 + 引用完整性 validator

**`task_spec.py`** 瘦身：删除网格规格、求解器设置、验收标准；只留任务 ID、名称、结果文件路径、单位制、规范引用。

**`report_spec.py`** 瘦身：删除审批流程、审核人、状态跟踪；只留项目元数据、模板 ID、章节列表、生成时间、关联 EvidenceBundle ID。

### 6.3 API 端点重组（5+1 上限）

```
POST /api/v1/projects                  # 创建项目
POST /api/v1/projects/{id}/results     # 上传结果文件，自动检测 reader
POST /api/v1/projects/{id}/draft       # 触发草稿生成（流式 WebSocket）
GET  /api/v1/projects/{id}/draft       # 获取当前草稿（含证据 sidecar）
POST /api/v1/projects/{id}/export      # 导出 .docx
GET  /api/v1/health                    # 健康检查（Electron Main 用）
```

### 6.4 6 周迁移行军图

| 周 | 末态验证 |
|---|---|
| Week 1 | 桶 A 重构 + 桶 C 删除 + 桶 E 清理 + Layer 2/3 schema 写完。`pytest` 跑通；`grep -r "from app.parsers.result_parser"` 返回空 |
| Week 2 | CalculiX adapter 重构完成；GS-001 端到端跑通：σ_max 与解析解 7.5 MPa 偏差 < 5% |
| Week 3 | Nastran adapter（pyNastran 包装）+ GS-002 跨 solver 一致性测试通过 |
| Week 4 | Electron 壳 + Python subprocess 通信；本地 dev 模式跑通"按钮 → 后端健康检查" |
| Week 5 | Windows 打包流水线 + EV 签名 + auto-updater；CI 出 .exe，Win10/11 双击不被 SmartScreen 拦截 |
| Week 6 | ANSYS adapter + GS-003 + LLM 代理 v0；端到端：拖入 .frd/.rst/.bdf → 模型摘要 → AI 段落生成 |

### 6.5 完成度闸门（6 条硬性，任一不达标不发种子 Alpha）

1. `result_parser.py` / `api/result.py` 不存在；旧 import 全部清零
2. `core/types/` 至少 6 enum + 5 dataclass，`mypy --strict` 通过
3. CalculiX/ANSYS/Nastran 三 adapter 通过 GS-001/002/003 跨 solver 一致性测试（max stress 偏差 < 1%、max disp 偏差 < 0.5%）
4. Abaqus 至少 stub + 用户文档（odb_export.py helper 路径明确）
5. Windows .exe：CI 自动产出、EV 签名、SmartScreen 不告警、`%LOCALAPPDATA%` 安装、< 5 秒启动
6. LLM 代理在 Aliyun ECS 跑通；UI 上有数据披露弹窗

### 6.6 并行非技术工作（迁移期不能停）

- **Week 1–4**：种子用户漏斗（按第 3 章），Week 6 末必须有 ≥2 个明确愿意装 Alpha 的种子工程师
- **Week 1**：EV 代码签名证书申请（审核 1–2 周）
- **Week 1**：Aliyun ECS + 通义 API 配额（企业认证可能要时间）
- **Week 1–4**：3 个内置模板的 .docx 起草

### 6.7 5 个迁移期高频陷阱

1. 想"两条腿走路"：新旧并行 = 两套都不完整。**强迁移**
2. 抽象层先于使用案例做完美：允许 Week 4 ANSYS 接入时做一次小幅修订，之后冻结
3. 拖着 `_frozen/` 不结清：每文件 README 写明 expiration（M4 启用 / M6 删除 / 永不）
4. Electron 与 Python 版本不锁死：`.python-version` + `requirements.lock` 锁到 patch 版本
5. 迁移期忽略种子用户接触：(b) 与 (e) 必须并行，每周 8 小时留给接触

---

## 7. ADR 索引（架构决策汇总）

| ID | 决策 | 章节 |
|---|---|---|
| ADR-001 | 派生量永远不在 Layer 1（adapter）算 | §4.8 |
| ADR-002 | CanonicalField 是闭集，扩展走 RFC | §4.8 |
| ADR-003 | adapter 不做启发式补全，单位 UNKNOWN 必须由用户选 | §4.8 |
| ADR-004 | adapter 不做缓存、不做 IO 优化 | §4.8 |
| ADR-005 | 加新 solver 必先加新 GS 黄金样本 | §4.8 |
| ADR-006 | 桌面框架选 Electron | §5.1 |
| ADR-007 | Python 打包用 Embedded CPython | §5.3 |
| ADR-008 | LLM 必须自建 Aliyun 代理，绝不嵌 API key | §5.5 |
| ADR-009 | 仅支持 Windows，macOS/Linux 推迟到 M6+ | §5.8 |
| ADR-010 | 不做 chat 界面、不做 RAG（MVP 阶段） | §2.3 |
| ADR-011 | 不做 LLM 算数 | §2.3 |
| ADR-012 | LLM 输出强制挂载证据 ID | §2.4 |

---

## 8. 后续阶段路线图（信息性，非冻结）

| 阶段 | 时间 | 目标 |
|---|---|---|
| M1–M2 | 信任地基 | 抽象层 + Electron + CalculiX/ANSYS reader + LLM 代理 |
| M3 | MVP 上线 | 30 分钟敢签字，5 种子产出 ≥5 份签字报告 |
| M4–M6 | 后处理探索 | 启用 RAG / 知识库；Pro 版定价开打；扩展模板库 |
| M7–M12 | 跨求解器深度 + 团队版 | Abaqus 完整支持、Nastran 上线；Team 版（项目空间、协作） |
| M13–M18 | 前处理副驾 | 网格质量评估、BC sanity check、参数化研究助手（不替代前处理 GUI） |

---

## 附录 A：术语表

| 术语 | 定义 |
|---|---|
| Wedge | PLG 项目的尖锐切入点，痛感强到用户愿意自费 + 主动安利同事 |
| EvidenceBundle | 一份报告所有"证据项"的有序集合，提供可追溯性 |
| CanonicalField | 跨 solver 统一的物理量名词表（白名单制） |
| ReaderHandle | 任何 solver adapter 必须实现的 Layer 2 协议 |
| GS (Golden Sample) | 黄金样本，用于 cross-solver 一致性测试的物理基准案例 |
| SI_mm 单位制 | 设计院最常用：mm + MPa + tonne + N + s |

## 附录 B：黄金样本清单（必须建设）

| ID | 物理问题 | 用途 |
|---|---|---|
| GS-001 | 简支梁静力学 | 已有，用作端到端 smoke test |
| GS-002 | 厚壁圆筒内压 | 验证应力张量跨 solver 一致性 |
| GS-003 | 吊耳强度 | 设计院最高频场景 |
| GS-004 | 压力容器局部应力 | ASME VIII Div 2 应力线性化路径准备 |
| GS-005 | 设备基础静力 | MVP wedge 直接对应场景 |

每 GS 必须包含 4 个 solver 的输入文件 + 结果文件 + 解析解（如可推导）+ 容差定义。

## 附录 C：API 端点清单（MVP 上限）

```
POST   /api/v1/projects                # 创建项目
POST   /api/v1/projects/{id}/results   # 上传结果文件
POST   /api/v1/projects/{id}/draft     # 触发草稿生成（WebSocket 流式）
GET    /api/v1/projects/{id}/draft     # 获取当前草稿
POST   /api/v1/projects/{id}/export    # 导出 docx
GET    /api/v1/health                  # 后端就绪检查
```

新增 API 必须经 RFC-002+ 流程评审。

## 附录 D：技术栈版本锁

| 组件 | 版本 |
|---|---|
| Python | 3.12.x（patch 版本由 `.python-version` 锁定） |
| Node.js | 20 LTS |
| Electron | 最新 stable |
| FastAPI | 0.110+ |
| Pydantic | 2.5+ |
| pyNastran | 1.4+ |
| ansys-mapdl-reader | 0.53+ |
| h5py | 3.10+ |
| python-docx | 1.1+ |

## 附录 E：术语 - Founder-led 不可委托清单

1. 候选种子用户初次访谈（前 30 次）
2. 5 人种子微信群 24 小时盯守
3. 每周日晚手写"种子用户周报"
4. 每周三 20:00 Office Hour
5. 每月轮访 1 个种子用户城市

---

## 修订历史

| 版本 | 日期 | 修订人 | 说明 |
|---|---|---|---|
| v1.0 | 2026-04-26 | 项目核心组 | 初版冻结 |

---

**本文档为 FROZEN 状态。任何修改必须通过 RFC-002+ 流程，不得直接编辑本文。**
