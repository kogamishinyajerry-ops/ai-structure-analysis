# RFC-001 W6 路线图：从"出 DOCX"到"敢签字"

| 字段 | 值 |
|---|---|
| 文档编号 | RFC-001-W6-roadmap |
| 状态 | DRAFT — 待用户拍板 |
| 起草日期 | 2026-04-27 |
| 上游 | RFC-001 §2.2 步骤 4 / §2.5 质量基线 |
| 下游 | ADR-019 ~ ADR-024（待开） |

---

## 0. 一句话

W5f 把"看得到的东西"做齐了（mesh / displacement / von_mises 三张图 + Electron 即时画廊），下一步是把**工程师签字所必须的判定数据**做齐：材料 → 许用应力 → PASS/FAIL → 边界条件溯源 → 一致性自检。**没有这一波，DOCX 不能签字，wedge 不成立。**

---

## 1. 现状盘点（2026-04-27 PR #90 待 merge）

| RFC-001 §2.2 步骤 4 要求 | 当前状态 | 缺口 |
|---|---|---|
| 模型概况（节点/单元/类型分布/网格尺寸） | ⚠ 部分（parsed 已有，DOCX 章节缺） | 加章节，不需新数据 |
| **材料属性表** | ❌ 全缺 | 数据模型只有 E/ν，没有 σ_y/σ_u；UI 无入口 |
| **边界条件汇总** | ❌ 全缺 | .frd 不含 BC，需读 .inp 旁路文件 |
| 关键结果数值（最大位移/Mises/主应力/**安全系数**） | ⚠ 数值有，**安全系数无**（无 σ_allow） | 加 allowable lookup + SF 计算 |
| 4 张标准图（mesh/BC/Mises/变形） | ⚠ 3 张（缺 BC 示意图） | W6d 顺手补 |
| 结果一致性自检 | ❌ 全缺 | numeric cross-check + flag |
| **工程结论 PASS/FAIL** | ❌ 全缺 | 接 SF + 阈值 → 出固定句式 |

签字阻塞排序（排序原则：**没有它工程师就不签**）：

1. ❌ **材料 σ_y/σ_u** — 没材料强度，安全系数无意义
2. ❌ **σ_allow 查表** — 没许用应力，PASS/FAIL 无法判
3. ❌ **PASS/FAIL 句式 + 规范引用** — 没结论段落，DOCX 是流水账不是评定
4. ❌ **边界条件汇总** — 审稿人第一眼问"约束在哪、载荷怎么加"，没答案不签
5. ⚠ 模型概况 + 一致性自检 — 体感分，但没有它仍能签

---

## 2. 决策：W6a–W6f 六个 PR 的目标 / 顺序 / 结束态

每个 PR 一周以内、≤500 LOC、依赖关系清晰。**先做硬阻塞（W6a-c），再做体感（W6d-f）。**

### W6a · 材料属性数据模型 + UI 入口 + DOCX 章节

**目标**：让工程师在 Electron 表单里输入 / 选择材料，DOCX 渲染"材料属性表"章节。

- 数据模型：`Material` 扩 `yield_strength`, `ultimate_strength`, `code_grade`, `code_standard`（"GB"/"ASME"），冻结。
- 内置材料库：`backend/app/data/materials.json` 收录设计院常用 10–15 种钢（Q235B/Q345B/16MnR/SA-516-70/SA-105 等），每种含 E/ν/ρ/σ_y/σ_u/规范引用。**只读，不允许 LLM 改。**
- UI：Electron 加 dropdown 选择材料，或自定义"自由输入"（自由输入打 `[需工程师确认]` flag）。
- DOCX：新增 §"材料属性"章节，渲染 Material 数据 + 规范引用。
- 测试：3 用例（dropdown / 自由输入 / 缺失）。

**结束态**：GS-001 demo 选 Q345B → DOCX 出现"材料属性: Q345B (GB/T 1591) E=2.1×10^5 MPa, σ_y=345 MPa"。

### W6b · 许用应力查表（GB 150 / ASME VIII Div 2）

**目标**：从材料 + 设计依据规范 → 算 σ_allow。

- 实现 `compute_allowable_stress(material, code, temperature)` 函数：
  - GB 150：σ_allow = min(σ_y/1.5, σ_u/3.0)（常温简化版，有引用）
  - ASME VIII Div 2 Table 5A：σ_allow = min(σ_y/1.5, σ_u/2.4)（常温简化版）
  - **温度查表 M4 再做**，MVP 锁定常温（注 `[假设: 常温 20°C]`）。
- 数据：`backend/app/data/allowable_stress_*.yaml` 内嵌简化版常温表，规范条款引用必须显式（条款号 + 页码）。
- 测试：4 用例（Q345B-GB / SA-516-70-ASME / 缺规范 / 异常温度）。

**结束态**：调 `compute_allowable_stress(Q345B, "GB", 20)` 返回 `(230 MPa, "GB 150-2011 §4.1.5")`。

### W6c · PASS/FAIL 判定 + 工程结论段落（确定性句式 + LLM 微调措辞）

**目标**：把 σ_max（已有）/ σ_allow（W6b）/ SF=σ_allow/σ_max → 固定句式 PASS/FAIL 段。

- 实现 `compute_verdict(sigma_max, sigma_allow, threshold=1.0)` → `{verdict: "PASS"/"FAIL", safety_factor: float, margin_pct: float}`。
- DOCX 新增 §"评定结论"章节：
  - PASS 句式：`"经核算，最大 Mises 应力 σ_max = {x} MPa，许用应力 [σ] = {y} MPa（依据 {规范条款}），安全系数 SF = {z} ≥ 1.0，**评定结论：合格**。"`
  - FAIL 句式：触发"建议"段（RFC-001 §2.2 步骤 4 LLM 生成器，受约束）。
- LLM 只允许微调措辞（受 prompt 约束 + 4 evidence items 强制注入，不允许填数值）。
- 测试：3 用例（PASS / FAIL / 缺 σ_allow → 输出 `[需工程师补充]`）。

**结束态**：GS-001 demo（σ_max ≈ 50 MPa, σ_allow=230 MPa）DOCX 末段出现"评定结论：合格 (SF=4.6)"。

### W6d · 边界条件汇总（读 .inp 或 user-supplied YAML）

**目标**：DOCX 出现"边界条件汇总"章节，列出约束 / 载荷类型 + 位置 + 量级。

- L1 reader：扩展 `FRDParser` 兼容旁路 `.inp` 解析（`*BOUNDARY` / `*CLOAD` / `*DLOAD` 块），或允许用户上传 `bc.yaml`。
- BC 数据走已有的 `BoundaryCondition` Layer-3 protocol（`backend/app/core/types/domain.py`）。
- DOCX 章节：表格 — `编号 | 类型 | 作用位置 (NSET/ELSET) | 分量 | 单位`。
- viz：在 W5f mesh 图上加一个 `render_bc_overlay`（红色箭头表力，绿色三角表约束）— **不阻塞 W6d landing**，BC 文字章节先出。
- 测试：3 用例（GS-001 .inp / 缺 .inp 输出占位章节 / 自定义 bc.yaml）。

**结束态**：GS-001 DOCX 出现"边界条件: 1) 固定约束 (NSET=fixed_bottom, 60 节点); 2) 压力载荷 (ELSET=top_face, 5 MPa)"。

### W6e · 模型概况章节 + 单元类型分布

**目标**：DOCX 顶部加"模型概况"章节，节点数 / 单元数 / 单元类型 distribution / 网格尺寸特征长度。

- 数据已在 `parsed`，纯 DOCX 章节工作。
- 网格尺寸：用 `bbox_diag / N^(1/3)` 作为 representative element size，注 `[估算]`。
- 测试：2 用例（GS-001 / 空网格容错）。

**结束态**：DOCX 出现"模型概况: 36 节点 / 10 单元 (HEX8) / 特征尺寸约 25 mm"。

### W6f · 一致性自检（numeric cross-check + flag）

**目标**：DOCX 末加"自检报告"sidebar，列出本份 DOCX 中所有数值的来源 evidence_id + 一致性校验结果。

- 实现 `consistency_check(parsed, evidence_bundle)` → list of `{check_name, status, expected, actual, message}`。
- 内置检查：
  1. σ_max 在 stress dict 中确实存在（不是被 LLM 编出来的）
  2. 单位制一致（si-mm 全程不混 si）
  3. 节点数 = 单元拓扑里出现的 unique node 数
  4. SF 值 = σ_allow / σ_max（重算一次校核 LLM 没改数）
- 任一 FAIL → DOCX 顶部加红字"⚠ 自检失败，工程师须复核"。
- 测试：4 用例（全 PASS / 单位混合 / σ_max 不一致 / SF 重算偏差）。

**结束态**：GS-001 DOCX 末附 §自检报告 4 项全 PASS。

---

## 3. 不做清单（W6 阶段守住边界）

- ❌ 温度依赖材料数据（M4+）
- ❌ 自动判合规（法律责任问题，RFC-001 §2.3 已禁）
- ❌ AI 审核工程师写的内容（同上）
- ❌ 多材料 / 多 BC 组合优化（M4+）
- ❌ ANSYS .rst 真接入（保持 stub，M4 完整）
- ❌ Electron-builder 打包（ADR-018 已 deferred 到非 dev evaluator 阶段）
- ❌ Mesh Protocol revisit（M4+，目前 W3 抽象层够用）

---

## 4. 节奏 / 验收

- **每个 PR 单 reviewer 流程**：Codex R1 → 改 → R2 → merge（per RETRO-V61-001 risk-tier triggers，W6a-c 全部触发硬性 Codex review）。
- **Self-pass-rate 诚实原则**：W6a 估 60%（材料数据模型简单但 UI 改动多），W6b 估 50%（许用应力规范引用易踩坑），W6c 估 40%（LLM 段落最易出错），W6d 估 50%（.inp 解析复杂），W6e 估 80%（纯渲染），W6f 估 70%。**任何 ≤70% 必须 pre-merge Codex**。
- **结束验收**：W6f 落地后跑一次 GS-001 demo，DOCX 必须包含 7 个章节（项目信息 / 模型概况 / 材料属性 / 边界条件 / 结果云图 / 关键结果 / 评定结论），4 张图，1 份自检 sidebar。**找一位真种子工程师做 30 分钟测试**，记录是否签字。

---

## 5. 待用户决策的开放问题

1. **材料库覆盖范围**：W6a 内置 10–15 种钢够吗？还是要含铸铁 / 不锈钢 / 铝合金？（影响 W6a LOC，建议先锁碳钢 + 低合金钢）
2. **规范优先级**：W6b 先 GB 还是先 ASME？（建议 GB 先，原因：种子用户 90% 化工 / 电力，主用 GB 150 / GB 50017）
3. **PASS/FAIL 阈值**：W6c 阈值用 SF≥1.0（许用应力本身已含安全系数），还是设计院习惯再加 1.5？（建议 SF≥1.0，与规范一致；额外余量由工程师在结论段补充）
4. **BC 数据来源**：W6d 优先 .inp 解析还是 bc.yaml 用户输入？（建议 .inp 先，GS-001 已有 .inp；bc.yaml 留 fallback）
5. **LLM 模型选型**：W6c 工程结论段落用本地 Ollama 还是阿里云 LLM？（RFC-001 §5 倾向阿里云代理，但 LLM 签字材料属于敏感内容，可能需本地）
6. **节奏**：W6a-f 一次性立 6 个 ADR 还是按 W6a 起步先看效果？（建议先 W6a 立 ADR-019，落地后再起 W6b ADR-020）

---

## 6. 我推荐的下一步（请用户拍板）

**方案 A（保守）**：先合 PR #90（W5f viz tracking）→ 起草 ADR-019（W6a 材料数据）→ 等 Codex 回血后开始 W6a。
**方案 B（激进）**：先合 PR #90 → 同时开 ADR-019 (W6a) + ADR-020 (W6b) 双线，Codex 回血后批量审。
**方案 C（最稳）**：暂不合 PR #90（self-pass-rate=30% 必须 pre-merge Codex），等 Codex 回血先审 #90，**通过后**再启 W6a。

**我倾向方案 C**：30% 自评 + 13 文件 + 969 LOC 的 PR 不该靠 CI 绿就 merge，等 Codex (Apr 29 10:50) 后再走，期间用这两天起草 ADR-019 (W6a) + 内置材料库 JSON 数据。

---

## 修订历史

| 版本 | 日期 | 内容 |
|---|---|---|
| 0.1 | 2026-04-27 | 初稿，待用户决策开放问题 1–6 + 方案 A/B/C |
