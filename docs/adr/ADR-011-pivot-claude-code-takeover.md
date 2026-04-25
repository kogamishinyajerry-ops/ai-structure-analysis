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

任一触发即 **STOP + 召回 T0 Gate + 回滚未推送 commit**。

| ID  | Trigger | Detection | Recovery |
|-----|---------|-----------|----------|
| HF1 | Diff 触及 forbidden zones (`agents/solver.py`, `tools/calculix_driver.py`, `golden_samples/**`, 治理类 docs 未先开 ADR) | pre-commit hook + CI path-guard | 立即 `git reset --soft`，先开 ADR / 申请 Gate |
| HF2 | 单会话 drift > 5 turns / 40k tokens / 3 files / 500 LOC 且未拆分 subagent | T1 自检 + claude-hud 计数 | 当前 turn 结束前必须 spawn subagent；否则停手 |
| HF3 | 新增 sample 无 golden-standard 引用 | sample registry schema 校验 | 标记 `insufficient_evidence`，不进入回归集 |
| HF4 | Artifact 落入 Decisions DB 但 Notion Handoff 缺失 | Notion sync diff 检查 | 回滚 Decisions 记录；补 Handoff 后重发 |
| HF5 | Codex verify 结论与 repo 真值不一致 | `Codex-verified` trailer vs git diff 校验 | T0 Gate 召回；以 repo 为准修 Notion / Codex 上下文 |

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
2. **Subagent 边界违规成本** — Allowed/Forbidden 描述不准会导致 rollback；缓解：HF1 路径守卫前置。
3. **In-flight S2.1-02 collision (watch-item)** — 本 ADR 的首次 Notion sync 可能与 `feature/AI-FEA-S2.1-02-notion-sync-contract-align` 的契约迁移在 Notion DB schema 上撞车。**主 session 须在 commit 前手工核对 FF-01b**（"先验证 S2.1-02 是否已合并；未合并则 ADR-011 的 Notion 同步走旧契约，并在 ADR 里补一条 follow-up 标注"）。
4. **HF2 误判** — 5/40k/3/500 阈值可能在大型 schema refactor 时过早触发；首 4 周允许 T1 在每次触发时附 30 字理由继续，统计真实违规率，再决定是否调阈 [verify]。
5. **T0 召回延迟** — Gate 是人工触发，深夜事件可能滞留；明确 SLA 由后续 ADR 补。

---

## Rollback

观察窗口 4 周。若出现以下任一：

- Codex verification mismatch rate **> 15%**（HF5 触发频次 ÷ 总 verified claim 数）；或
- Subagent 边界违规导致 **> 2 次 HF1 触发**；

则升级到 T0 (Opus 4.7) 架构审查，重新评估是否需要引入第二条模型通道（候选：Codex 提升为受限的 main-code 提交者，或重新启用 Antigravity 作为只读 review 通道）。Rollback 通过新 ADR (ADR-{nnn}-revoke-011) 形式落地，本 ADR 标记为 Superseded。

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

## Cross-References

- Phase 1.5 Foundation-Freeze 任务集 **FF-01 .. FF-05**；本 ADR = **FF-01**（governance baseline）。
- In-flight branch **`feature/AI-FEA-S2.1-02-notion-sync-contract-align`** — 本 ADR 不阻塞，独立分支落地；FF-01b 由主 session 手工核对契约对齐。
- **GS-001 / GS-002 / GS-003** deviation attribution = **FF-02**，是 Phase 2 Web Console 激活的硬前置（本 ADR 不直接修 GS，仅授权 FF-02 开工）。
- 本仓库 `README.md` 的 5 development rules 与本 ADR 的 9 Golden Rules 一致；后续如有冲突以 ADR 为准。
- `docs/architecture.md` 与 `docs/well_harness_architecture.md` 的四层架构图与本 ADR 第 9 条 Golden Rule 对齐。
- Notion 控制塔页：[AI StructureAnalysis 项目中枢](https://www.notion.so/AI-StructureAnalysis-345c68942bed80f6a092c9c2b3d3f5b9) (root_page_id `345c68942bed80f6a092c9c2b3d3f5b9`，已与 `config/well_harness_control_plane.yaml` 对齐)。
