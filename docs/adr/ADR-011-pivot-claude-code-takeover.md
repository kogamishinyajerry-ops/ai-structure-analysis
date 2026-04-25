# ADR-011: Pivot to Claude Code CLI Single-Path Governance

- **Status:** Accepted
- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — human-confirmed
- **Date:** 2026-04-25
- **Supersedes:** ADR-000 template's `Decider: Antigravity / Gemini 3.1 Pro` line; prior routing memos (TBD by main session — placeholder until FF-03 inventory completes)
- **Related Phase:** 1.5 Foundation-Freeze (FF-01)
- **Branch:** `feature/AI-FEA-ADR-011-pivot-claude-code-takeover` (lands independently of in-flight `feature/AI-FEA-S2.1-02-notion-sync-contract-align`)

---

## Context

AI-Structure-FEA was bootstrapped on a triple-model split: Antigravity (Claude Sonnet 4.6) drove daily development, Gemini 3.1 Pro handled architecture review, and Gemini 3 Flash served as a fast-path assistant. The intent was to load-balance across vendors, but in practice the three drivers produced **coordination friction without proportional throughput gain**:

- 多模型上下文不一致：Antigravity 的 working tree 状态与 Gemini 3.1 Pro 的 review session 经常错位，导致 ADR / 代码 / 测试三方的真值口径不统一。
- 无单一可问责执行路径：当 GS-001 / GS-002 / GS-003 三个 golden samples 全部停留在 `pending_review` 时，没有任何一个模型能独立闭合"deviation 归因 → 修复 → 回归"的循环。每个模型都只承担局部责任。
- Phase 1.5 Foundation-Freeze 窗口（48h）要求在 Phase 2 Web Console 启动前完成治理收口；当前的三模型路由无法在窗口期内交付一份对 commit、Notion、运行时三方都可审计的执行链。
- 上下文窗口压力下沉：Antigravity 的 Sonnet 4.6 默认上下文不足以一次性承载 `agents/` 六阶段 DAG + `schemas/` + `well_harness/` 的全景，频繁的 context reset 导致决策碎片化。

证据集中体现在三个 golden samples 上：GS-001 / GS-002 / GS-003 在 `golden_samples/` 下均已就位，但 deviation attribution 报告至今未落盘到 ADR — 这是 Phase 2 Web Console 激活的硬前置条件 (FF-02)。在评审中可以看到，每个模型都"读过"样本，但没有任何一个模型对偏差归因负最终责任。

与此同时，`feature/AI-FEA-S2.1-02-notion-sync-contract-align` 分支正在迁移 Notion sync 契约（详见 `docs/runbook-schema-migration.md`）。这条分支不能被本 ADR 阻塞，但它也佐证了"治理路径必须先稳定，否则契约迁移完成后没有合法的 handoff 通道接收"。

因此，Phase 1.5 的 governance closure 必须先解决一个问题：**谁是这个项目里唯一对"代码已落地"负责的执行体**。

---

## Decision

收敛到 **三层路由 (T0 / T1 / T2)**，每一层职责单一、入口唯一：

- **T0 — Architecture Gate**：Claude Opus 4.7（fallback 4.6），仅通过 Notion 异步会话调用，**人工触发**。负责跨阶段架构决策、ADR 终审、HF 规则争议裁决。不接管日常开发。
- **T1 — Primary Execution**：**Claude Code CLI (Opus 4.7, 1M context)** — 项目内**唯一强制开发入口**。所有 Edit / Write / Bash 必须从这里发起；所有 commit 必须带 `Execution-by` trailer。1M 上下文允许它一次性持有 `agents/` + `schemas/` + `runs/` 全景，消除三模型时代的 context fragmentation。
- **T2 — Joint-Dev Peer & Independent Verifier**：**Codex GPT-5.4-xhigh** — 仅承担**关键 claim 的独立验证**与并行辅助 research。**不允许直接对 main-code 提交**。验证结果以 `Codex-verified: <claim-id>@<sha>` trailer 形式回写，由 T1 在 commit 时引用。

**Banned routes (硬禁止)：** Antigravity (任何模型) / Opus 直接开发 / MiniMax-2.7 / GPT 直接执行 / Codex 直接 main-code 提交。

**Subagent 隔离规则：** T1 任一任务超过 **5 turns / 40k tokens / 3 files / 500 LOC** 任一阈值，必须委派给 subagent，并在委派 prompt 中显式声明 `Allowed:` 和 `Forbidden:` 文件边界。Subagent 只读不写时无需声明 Forbidden（默认全部 Forbidden）；写入时必须列举具体路径。

---

## Hard-Floor Rules (HF1 – HF5)

任一 HF 触发即 **STOP + 召回 T0 Gate + 回滚未推送 commit**（HF2 例外见 §Calibration Mode）。

**Forbidden zone (HF1) 完整清单** (扩展自 Codex R1 SHOULD_FIX #1，去除盲区)：

- `agents/solver.py`, `tools/calculix_driver.py` — 求解器实现
- `agents/router.py` — ADR-004 fault routing
- `agents/geometry.py` — ADR-008 N-3 dummy-geometry guard
- `schemas/sim_state.py` — ADR-004 FaultClass enum (downstream 类型契约)
- `tests/test_toolchain_probes.py` — ADR-002 toolchain pin assertion
- `Dockerfile` + `Makefile` 中 `docker-base` / `docker-probe` / `hot-smoke` 段 — ADR-002 CalculiX 2.21 pin (`docker-probe` 同样在 forbidden zone 内：它消费 `docker-base` 镜像跑 toolchain probes，是 ADR-002 pin 的执行验证点)
- `golden_samples/**` — 全部只读
- `docs/governance/**`, `docs/adr/**` — 必须先开新 ADR 或在已有 ADR 加 supersede

| ID  | Trigger | Detection (现状 / 目标) | Recovery |
|-----|---------|------------------------|----------|
| HF1 | Diff 触及上方 forbidden zone 任一路径 | **现状**：T1 自检 + PR review；**目标**：pre-commit path-guard + CI 二次校验（FF-06 跟踪） | 立即 `git reset --soft`，先开 ADR / 申请 Gate |
| HF2 | 单会话 drift > 5 turns / 40k tokens / 3 files / 500 LOC 且未拆分 subagent | T1 自检 + claude-hud 计数（手动） | 4 周 Calibration Mode 期内可附 ≤30 字理由继续；之后强制 spawn subagent，否则停手 |
| HF3 | 新增 sample 无 golden-standard 引用 | **现状**：人工 PR review；**目标**：sample registry schema 校验 + CI（FF-08 跟踪） | 标记 `insufficient_evidence`，不进入回归集 |
| HF4 | Artifact 落入 Decisions DB 但 Notion Handoff 缺失 | **现状**：Notion sync 脚本输出对账 + 人工核对；**目标**：notion_sync.py 端到端 diff 守卫（已部分实现，contract 迁移 in-flight on `feature/AI-FEA-S2.1-02-notion-sync-contract-align`） | 回滚 Decisions 记录；补 Handoff 后重发 |
| HF5 | Codex verify 结论与 repo 真值不一致 | **现状**：人工对账（Codex 报告 vs `git diff`）；**目标**：`Codex-verified` trailer 存在性 + claim-id 校验 hook（FF-07 跟踪） | T0 Gate 召回；以 repo 为准修 Notion / Codex 上下文 |

### Enforcement Maturity (Codex R1 BLOCKING #1 回应)

ADR-011 v1 把 HF1/HF5 的 Detection 写成既成事实是 **过度声明**。当前 `.pre-commit-config.yaml` 仅含 `ruff`，CI 仅含 lint+pytest，**没有 path-guard、没有 trailer-presence 校验**。在自动化检测落地前，HF 规则的 enforcement 实际是：

1. **T1 自检**（每条 commit 前 T1 主动检查 forbidden zone diff、subagent trailer 完整性）
2. **PR review**（人工对照本 ADR 的 forbidden-zone 清单复核）
3. **post-merge audit**（Codex 周期性抽查最近 N commit 的 trailer 与 zone 边界）

跟踪任务（必须在本 ADR Accept 后 ≤ 4 周内排期）：

- **FF-06**：`pre-commit` hook 实现 forbidden-zone path-guard（HF1 detection automation）
- **FF-07**：CI 实现 commit trailer presence + claim-id 格式校验（HF5 detection automation）
- **FF-08**：`golden_samples/<id>` registry schema 校验（HF3 detection automation）

在 FF-06/07/08 落地前，**任何 HF 触发依赖 T1 主动声明 + PR review 复核**。这是 honor-system，而非可审计控制 — Codex R1 BLOCKING #1 已正确指出。

### Calibration Mode (HF2 解除自相矛盾)

ADR-011 v1 在 §Hard-Floor 表述 "STOP" 同时在 Risks §4 允许 4 周内附理由继续 — Codex R1 SHOULD_FIX #2 正确指出这是矛盾。本节明确：

- **Calibration window**: 2026-04-25 → **2026-05-23**（4 周）
- 期内 HF2 触发 = T1 在该 turn 内附 ≤30 字理由 + 在 `reports/hf2_calibration.md` 追加一行；可继续。
- 期后 HF2 触发 = 真 STOP；必须当场 spawn subagent 或停手。
- Calibration window 结束时，T1 必须基于 `reports/hf2_calibration.md` 提交 mini-retro，**决定是否调阈**或维持 5/40k/3/500。

在 calibration window 内 HF2 是 **soft floor**，期后回归 hard floor。其他 HF 不受此例外影响。

---

## 9 Golden Rules

1. **Three-tier SSOT immutable** — Code SSOT = `github.com/kogamishinyajerry-ops/ai-structure-analysis`；Process SSOT = Notion 项目中枢；Runtime SSOT = `runs/` + CI artifacts。三者冲突时以 git 为准，反向修 Notion / runs。
2. **CalculiX is the only numerical truth source** — 任何"等价求解器"声明必须先经 ADR + Gate。
3. **Every architecture decision lands as ADR immediately** — 沿用本仓库 `docs/adr/ADR-{nnn}-{slug}.md` 轻量约定（不复制 cfd-harness-unified DEC frontmatter）。
4. **Handoffs cannot bypass Notion** — 阶段间交接必须有可点开的 Notion Handoff 页。
5. **No golden-standard → no test** — 没有 GS 引用的样本一律 `insufficient_evidence`，不进 regression lane。
6. **Sessions fully traced** — 每个 commit 带 `Execution-by` trailer；subagent 任务带 `Subagent: <id>` 子项。
7. **Schema-first** — Pydantic v2 strict validation per `schemas/`；schema 变更先 ADR、再代码。
8. **Reversibility** — 每个决策必须文档化 rollback 路径（见各 ADR 的 Rollback 节）。
9. **Four-layer architecture** — Control / Execution / Knowledge / Evaluation；import 方向单向：Control 可读全部；Execution 仅依赖 Knowledge；Evaluation 独立于 Execution（不允许反向 import）。

---

## Commit Trailer Convention

所有进入 main 的 commit 必须携带：

```
Execution-by: claude-code-opus47 [· Subagent: <id>]
Codex-verified: <claim-id>@<sha>
```

- `Execution-by` 必填。无 subagent 时省略 `· Subagent:` 段。
- `Codex-verified` 在涉及 critical claim（数值正确性、schema 兼容性、forbidden-zone 边界）时必填；纯文档/格式 commit 可省略，但需在 PR body 说明。`<claim-id>` 在尚未生成时保留字面占位 `<claim-id>`，由 main session 在 review 阶段补齐。

---

## Consequences

### Benefits

1. **单一可问责执行路径** — `Execution-by` trailer 让任意 commit 都能反查到唯一的人/模型对账主体。
2. **协调延迟下降** — 三模型 → 单模型，消除"等另一边 review 完才能动"的串行等待。
3. **审计可闭合** — commit trailer + Notion ADR + `runs/` 三件套构成最小可审计单元。
4. **上下文窗口压力解耦** — 1M 主上下文 + subagent 隔离取代"频繁 context reset"，长任务可持续推进。
5. **盲点验证职责清晰** — Codex 只验不写，避免"既是开发者又是审查者"的角色冲突。

### Risks

1. **单驱动瓶颈** — 当 Codex 验证不可用（额度耗尽 / 服务异常）时，critical claim 无法获得独立验证；缓解：`cx-auto 20` 多账号自动切换。
2. **Subagent 边界违规成本** — Allowed/Forbidden 描述不准会导致 rollback；缓解：HF1 path-guard 前置（FF-06 automation 落地前依赖人工 review）。
3. **In-flight S2.1-02 collision (watch-item)** — 本 ADR 的首次 Notion sync 可能与 `feature/AI-FEA-S2.1-02-notion-sync-contract-align` 的契约迁移在 Notion DB schema 上撞车。**主 session 须在 commit 前手工核对 FF-01b**（"先验证 S2.1-02 是否已合并；未合并则 ADR-011 的 Notion 同步走旧契约，并在 ADR 里补一条 follow-up 标注"）。FF-01b 实测发现 Decisions DS 实际 schema 与 `notion_sync.register_decision()` 期望字段差距更大（缺 `Branch`/`Session Batch`/`ADR Link` 三项），S2.1-02 的 `Sprint` 添加并未对齐 — 应另开 ADR 修 schema。
4. **HF2 自相矛盾** — 见上方 §Calibration Mode（Codex R1 SHOULD_FIX #2 修复）。期内 soft floor，期后 hard floor；终止日期 2026-05-23 不可滑动。
5. **T0 召回延迟** — Gate 是人工触发，深夜事件可能滞留；明确 SLA 由后续 ADR 补（候选 SLA：工作日 4h，周末 24h；本 ADR 不强制）。
6. **Enforcement maturity gap** — HF1/HF5 现阶段是 honor-system（见 §Enforcement Maturity）。在 FF-06/07/08 落地前，治理可信度依赖 T1 自检 + PR review。Codex R1 BLOCKING #1 正确指出该差距；本 ADR 接受并以排期对冲，不靠装作已有 hook 来 over-claim。

---

## Rollback

观察窗口 4 周（2026-04-25 → 2026-05-23），与 Calibration Mode 同步。若出现以下任一（指标已加 denominator 与严重度分层，回应 Codex R1 BLOCKING #2）：

- **Codex verification mismatch rate > 15%**，**且**该周期内累积 verified claim ≥ 20。低于 20 时只记录、不触发 rollback（小样本不可靠）。
- **HF1 触发按区域加权 > 2 weighted points**，权重表 (覆盖 §HF1 forbidden zone 全部 8 类，无遗漏)：
  - solver core (`agents/solver.py`, `tools/calculix_driver.py`, `agents/router.py`, `agents/geometry.py`) = **1.0 / 次**
  - schema / toolchain pin (`schemas/sim_state.py`, `tests/test_toolchain_probes.py`, `Dockerfile`, `Makefile` 中 `docker-base`/`hot-smoke`/`docker-probe` 段) = **0.5 / 次**
  - governance docs (`docs/adr/**`, `docs/governance/**`) = **0.3 / 次**
  - golden_samples write (`golden_samples/**`) = **1.0 / 次**

  例：solver core 误改 1 次 + governance docs 越权 1 次 = 1.3 weighted points (未触发)；solver core 误改 2 次 = 2.0 (未触发，临界)；solver core 误改 3 次 = 3.0 (触发)；Makefile docker-base 段误改 5 次 = 2.5 (触发)。
- **HF2 calibration window 关闭后**，HF2 hard-stop 触发频次 > 1 / 周。

任一触发则升级到 T0 (Opus 4.7) 架构审查，重新评估是否需要引入第二条模型通道（候选：Codex 提升为受限的 main-code 提交者，或重新启用一个只读 review 通道）。Rollback 通过新 ADR (ADR-{nnn}-revoke-011) 形式落地，本 ADR 标记为 Superseded。

**记录责任** — calibration window 内由 T1 在 `reports/hf_audit_2026-04-25_to_2026-05-23.md` 累计每条 HF / verified claim 数据；FF-06/07/08 落地后转为自动统计。

---

## Routing Comparison

| Aspect | Before (Antigravity 三模型) | After (Claude Code single-path) |
|--------|------------------------------|----------------------------------|
| Primary driver | Antigravity (Sonnet 4.6) | Claude Code CLI (Opus 4.7, 1M) |
| Architecture review | Gemini 3.1 Pro (同步, 内嵌开发流) | Opus 4.7 via Notion (T0, 异步, 人工触发) |
| Independent verification | 无（review 与开发同源） | Codex GPT-5.4-xhigh (T2, verify-only) |
| Fast-path assistant | Gemini 3 Flash | Subagent (T1 内部委派, 同模型族) |
| Commit accountability | 多源, trailer 缺失 | 强制 `Execution-by` + 可选 `Codex-verified` |
| Context capacity | ~200k, 频繁 reset | 1M 主上下文 + subagent 隔离 |

---

## Known Gaps (Codex R1 NICE_TO_HAVE 回应 — 显式声明非默认存在)

以下治理元素 ADR-011 没有规定，且仓库当前不具备。未来 ADR 必须补：

1. **`main` 分支保护** — GitHub 端的 required-reviews / required-status-checks / disallow-force-push 设置；当前仅 `README.md:81` 声明 "all code via PR"，不可执法。Tracked: ADR-012 候选。
2. **PR review 状态机** — 本 ADR 没有规定 PR 必须经过 (a) Codex post-commit review (b) reviewer 至少 1 人 (c) 所有 conversation resolved 才能 merge 的状态流。Tracked: ADR-012 候选。
3. **Subagent 失败回滚 SOP** — 当 subagent 越界（HF1）、超时、或返回 INSUFFICIENT_EVIDENCE 时，T1 应当 (a) 不引用 subagent 输出 (b) 落 `reports/subagent_failures/` 记录 (c) 决定降级路径。本 ADR 没有具体 SOP。Tracked: ADR-013 候选。
4. **FailurePattern 与 ADR 的 promotion 路径** — FF-02 在独立分支 `feature/AI-FEA-FF-02-failure-patterns` 已经创建 `docs/failure_patterns/` 与 `FP-001/002/003`（见该分支 commit `020f2d3`）。本分支 (`feature/AI-FEA-ADR-011-pivot-claude-code-takeover`) 不包含这些文件 — 两个分支独立 PR review。FP → ADR 的 promotion 规则（什么时候一个 FP 必须升级为 ADR）未规定。Tracked: 与 ADR-012 合并。

## Cross-References

- Phase 1.5 Foundation-Freeze 任务集 **FF-01 .. FF-05**；本 ADR = **FF-01**（governance baseline）。R2 修订引入 **FF-06/07/08** automation 跟踪与 **R2 retro 任务**。
- In-flight branch **`feature/AI-FEA-S2.1-02-notion-sync-contract-align`** — 本 ADR 不阻塞，独立分支落地；FF-01b 实测发现 Decisions DS schema 缺 `Branch`/`Session Batch`/`ADR Link`，与 S2.1-02 的 `Sprint` 添加方向不一致，应另开 ADR 修 schema。
- **GS-001 / GS-002 / GS-003** deviation attribution = **FF-02**。Subagent 完成于独立分支 `feature/AI-FEA-FF-02-failure-patterns` (commit `020f2d3`，4 个新文件：`docs/failure_patterns/README.md` + `FP-001/002/003`)。本分支不携带这些文件；两个分支独立合入 main 后才能在 main 上同时观察到。FP 提议 GS 状态全部 → `insufficient_evidence`，是 Phase 2 Web Console 激活的硬前置之一。
- 本仓库 `README.md:79-86` 的 5 development rules 与本 ADR 的 9 Golden Rules **部分重叠** (Rules #1, #4 大致对应 README #1, #2; Rules #3, #5 对应 README #3, #5; Rules #2, #6, #7, #8, #9 在 README 中不存在或仅隐含)。后续 README 与 ADR 冲突时以 ADR 为准；同时跟踪 README 同步 (FF-09 候选)。
- `docs/architecture.md:7` 与 `docs/well_harness_architecture.md:23` 描述了系统组件与闭环，但 **未定义到可执法的 four-layer import 边界**。本 ADR 第 9 条 Golden Rule 是首次声明该边界 — 实际 lint enforcement (e.g. `import-linter`) 跟踪 ADR-012 候选。
- Notion 控制塔页：[AI StructureAnalysis 项目中枢](https://www.notion.so/AI-StructureAnalysis-345c68942bed80f6a092c9c2b3d3f5b9) (root_page_id `345c68942bed80f6a092c9c2b3d3f5b9`，已与 `config/well_harness_control_plane.yaml` 对齐)。
- **Codex R1 review report** — `reports/codex_tool_reports/adr_011_r1_review.md` (CHANGES_REQUIRED, addressed in R2 amendment)。
