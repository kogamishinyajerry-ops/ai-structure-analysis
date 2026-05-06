# ADR-011: Codex-Primary Linear/Symphony Governance

- **Status:** Accepted (amended 2026-04-25 per AR-2026-04-25-001; amended 2026-05-03 per AR-2026-05-03-001; amended 2026-05-06 per AR-2026-05-06-001)
- **Decider:** Human owner — Codex-primary workflow ratified by ENG-32 pilot and local Claude Opus audit
- **Date:** 2026-04-25 (R5 APPROVE), amended 2026-04-25, 2026-05-03, and 2026-05-06
- **Supersedes:** ADR-000 template's `Decider: Antigravity / Gemini 3.1 Pro` line; prior routing memos (TBD by main session — placeholder until FF-03 inventory completes)
- **Related Phase:** 1.5 Foundation-Freeze (FF-01)
- **Branch:** `feature/AI-FEA-ADR-011-pivot-claude-code-takeover` (R5 APPROVE) ; `feature/AI-FEA-ADR-011-amendments-AR-2026-04-25-001` ; `feature/ADR-011-amendment-AR-2026-05-03-001-no-date-deadlines` ; `codex/wf-00-codex-primary-pilot`
- **Amendment cycles:**
  - 2026-04-25 R1→R5 — original Codex review arc (FF-01 baseline)
  - **2026-04-25 AR-2026-04-25-001** — T0 ratified amendments to §T2 (Codex role rewording), §HF2 (subagent activity-type split), §HF1 (zone narrowing — `docs/adr/`/`docs/governance/` moved to PR-protected zone, `scripts/hf1_path_guard.py` self-protection + `.github/workflows/**` added), §Enforcement Maturity (post-FF-06 state model + CI port deferred to ADR-013), §Rollback (weighted-zone table updated to HF1.1-HF1.9 + separate PR-protected-zone bypass metric), §Known Gaps (ADR-012/013 number reassignment), §Cross-References (import-linter reference unbound), and §Calibration Mode (note that ADR-012 supersedes self-pass-rate honor-system)
  - **2026-05-03 AR-2026-05-03-001** — User directive: **all date-based deadlines are removed from project policy**. Gates may only be dependency- or task-completion-driven. Primary affected ADR sections: §HF1 (HF2 Detection column "calibration window through 2026-05-23" → "calibration window remains open until …"), §Enforcement Maturity (HF2/HF3/HF5 Status column dates removed; FF-07/FF-08/FF-09 hard prerequisites added — must merge before Phase 2 activation, before Calibration Mode close-out, and before any PR may claim HF5/HF3 automation; §"In summary" date removed), §Calibration Mode (calendar window replaced with explicit Boolean close-out predicate `((entries≥20 AND T0-accepted retro) OR T0 explicit close-out OR Phase_2_Gate_queued)` where `Phase_2_Gate_queued` is the single canonical event term defined inline in §Calibration Mode), §Rollback ("观察窗口 4 周" replaced with rolling Calibration window; HF2 post-close-out rate-of-occurrence trigger restated as "first 10 post-close-out T1 sessions/PRs" per Codex R1; date-anchored audit-log path replaced with `reports/hf_audit.md` rolling log + `reports/archive/hf_audit_window-NNN.md` monotonic counter naming rule), §Risks #4 ("终止日期 2026-05-23 不可滑动" rule deleted — HF2 calibration ends when close-out predicate is true, not when a calendar passes). Companion edits in same amendment cycle: ADR header metadata (lines 3-8 — Status / Date / Branch / Amendment cycles updated) and `reports/hf2_calibration.md` header line (calendar window → predicate-driven). No semantic change to HF1-HF5 trigger conditions, HF2 numerical thresholds (5 turns / 40k tokens / 3 files / 500 LOC), Rollback weighted-zone math, or M1-M5 trigger taxonomy — only the calendar-anchor is removed in favor of completion-anchor.
  - **2026-05-06 AR-2026-05-06-001** — User directive: Codex becomes the primary implementation agent for this repo; local Claude Opus 4.7 becomes reviewer/auditor, not owner/executor. Linear is the work-control truth; GitHub/repo is code truth; Notion is an architecture/control mirror after repo and Linear truth are settled. ENG-32 / WF-00 validated the chain on PR #126: Codex disposition + local Claude Opus audit both returned BLOCKER because PR #126's proposed root `AGENTS.md` would have reintroduced Apex/Claude ownership and Codex-as-delegated-worker policy. This amendment supersedes stale wording that says Claude Code CLI is the sole execution path or that Codex is verify-only.

---

## Context

AI-Structure-FEA was bootstrapped on a triple-model split: Antigravity (Claude Sonnet 4.6) drove daily development, Gemini 3.1 Pro handled architecture review, and Gemini 3 Flash served as a fast-path assistant. The intent was to load-balance across vendors, but in practice the three drivers produced **coordination friction without proportional throughput gain**:

- 多模型上下文不一致：Antigravity 的 working tree 状态与 Gemini 3.1 Pro 的 review session 经常错位，导致 ADR / 代码 / 测试三方的真值口径不统一。
- 无单一可问责执行路径：当 GS-001 / GS-002 / GS-003 三个 golden samples 全部停留在 `pending_review` 时，没有任何一个模型能独立闭合"deviation 归因 → 修复 → 回归"的循环。每个模型都只承担局部责任。
- Phase 1.5 Foundation-Freeze 窗口（48h）要求在 Phase 2 Web Console 启动前完成治理收口；当前的三模型路由无法在窗口期内交付一份对 commit、Notion、运行时三方都可审计的执行链。
- 上下文窗口压力下沉：Antigravity 的 Sonnet 4.6 默认上下文不足以一次性承载 `agents/` 六阶段 DAG + `schemas/` + `well_harness/` 的全景，频繁的 context reset 导致决策碎片化。

证据集中体现在三个 golden samples 上：GS-001 / GS-002 / GS-003 在 `golden_samples/` 下均已就位，但 deviation attribution 报告至今未落盘到 ADR — 这是 Phase 2 Web Console 激活的硬前置条件 (FF-02)。在评审中可以看到，每个模型都"读过"样本，但没有任何一个模型对偏差归因负最终责任。

与此同时，`feature/AI-FEA-S2.1-02-notion-sync-contract-align` 分支正在迁移 Notion sync 契约（迁移 runbook 仅在该分支存在，路径 `docs/runbook-schema-migration.md` — **本分支不可见**；两个分支独立 PR review）。这条分支不能被本 ADR 阻塞，但它也佐证了"治理路径必须先稳定，否则契约迁移完成后没有合法的 handoff 通道接收"。

因此，Phase 1.5 的 governance closure 必须先解决一个问题：**谁是这个项目里唯一对"代码已落地"负责的执行体**。

---

## Decision

收敛到 **Codex-primary + Linear work-control + Claude audit**：

- **Work-Control Truth — Linear**：Linear `Engineering` issues define scoped work, acceptance, blockers, evidence requirements, and proof/status comments. One eligible issue maps to one bounded run. Missing issue outcome, repository, acceptance, boundaries, or evidence makes the run ineligible until clarified.
- **Code Truth — GitHub/repo**：this repository is the code truth. All code and governance changes land through branches and PRs. No direct push to `main`, no self-approval, and no auto-merge.
- **Primary Execution — Codex**：Codex is the default implementation agent. Codex may edit repo files, run tests, prepare proof packets, and open PRs within explicit issue/user scope. Codex does not self-merge and does not claim completion beyond evidence.
- **Reviewer/Auditor — local Claude Opus 4.7**：Claude Opus reviews prepared packets, diffs, or high-risk decisions and returns `APPROVE`, `CHANGES_REQUIRED`, or `BLOCKER`. Claude Opus is not the default executor, not repo owner, and not a substitute for Linear/GitHub truth.
- **Architecture/Control Mirror — Notion**：Notion mirrors architecture and control-plane state after repo and Linear truth are settled. Notion writes require explicit confirmation and must not precede code/work-control truth.
- **Mandatory review triggers** still apply:
  - **M1.** PRs touching governance text (`AGENTS.md`, `docs/adr/**`, `docs/governance/**`, `docs/failure_patterns/**`, ADR amendments)
  - **M2.** PRs with non-trivial executable assertion (reverts, sign/direction math, CI claims, factual numerical computations)
  - **M3.** PRs claiming HF zone compliance (HF1/HF4 scope verification)
  - **M4.** PRs translating governance text into enforcement code (hooks, CI, validators, lints, schemas)
  - **M5.** Any PR opened while calibration ceiling ≤ 50% (per ADR-012)
- **Review output expected**：sign/direction correctness on diffs and math · factual claim verification (CI status, file counts, scope, "all-files-touched") · technical semantics · cross-reference integrity (ADR footnote ↔ script path, STATE.md ↔ repo HEAD, ADR number ↔ filename, Linear issue ↔ proof).

**Banned routes (硬禁止)：** Antigravity as default executor / Opus direct development by default / MiniMax for code execution / GLM-series default routing / direct main-code commits / Notion-first truth changes.

**Subagent 隔离规则 (amended per AR-2026-04-25-001 §5 — activity-type split)：**

The numerical thresholds (`> 5 turns / > 40k tokens / > 3 files / > 500 LOC`) remain the trigger surface, BUT they apply differently by activity:

- **MUST use subagent (mandatory at threshold):**
  - Multi-file research / dependency exploration / code archaeology
  - Planning, spec-drafting, CHANGE_PLAN authoring
  - Long-form synthesis of repo state (Notion handoff blocks, session summaries)
  - Adversarial / red-team review of T1's own work product

- **MUST NOT use subagent (regardless of threshold):**
  - Code-editing diff (Write/Edit) on tracked files — user must see serial diffs
  - Test authoring on tracked files
  - Notion control-plane writes (session-trace continuity)
  - Final commit-message authoring

- **Reconciliation pattern (canonical for tasks ≥ HF2 threshold AND code-editing):**
  1. **Subagent**: research + author `docs/plans/<task>-CHANGE_PLAN.md` (research, MUST-use)
  2. **Main session**: execute plan via serial Edit/Write (code-editing, MUST-NOT-subagent)
  3. **Codex pre-merge**: review BOTH the plan (semantic) and the diff (factual)

This is the FF-06 pattern T1 already used. Skill recipe to be codified at `docs/skills/subagent_split_recipe.md` (out of this PR's scope — bundled with FF-07).

When subagent IS used, the existing rule remains: prompt must explicitly declare `Allowed:` and `Forbidden:` file boundaries. Subagent 只读不写时无需声明 Forbidden（默认全部 Forbidden）；写入时必须列举具体路径。

---

## Hard-Floor Rules (HF1 – HF5)

任一 HF 触发即 **STOP + 召回 T0 Gate + 回滚未推送 commit**（HF2 例外见 §Calibration Mode）。

**Forbidden zone (HF1) 完整清单 — amended per AR-2026-04-25-001 §3 into two surfaces:**

**HF1 hard-stop zone** (pre-commit + CI both enforce; `scripts/hf1_path_guard.py` rejects staged diffs touching these paths):

- **HF1.1** `agents/solver.py`, `tools/calculix_driver.py` — 求解器实现
- **HF1.2** `agents/router.py` — ADR-004 fault routing
- **HF1.3** `agents/geometry.py` — ADR-008 N-3 dummy-geometry guard
- **HF1.4** `schemas/sim_state.py` — ADR-004 FaultClass enum (downstream 类型契约)
- **HF1.5** `tests/test_toolchain_probes.py` — ADR-002 toolchain pin assertion
- **HF1.6** `Dockerfile`, `Makefile` — ADR-002 CalculiX 2.21 pin. Caveat: ADR-011 v1 scoped HF1.6 to `docker-base` / `docker-probe` / `hot-smoke` sections, but `scripts/hf1_path_guard.py` enforces whole-file (parsing build-file syntax is out of scope). Section-level narrowing tracked as a follow-up ADR (number TBD), or alternative refactor: isolate protected targets into `Makefile.docker` / `Dockerfile.toolchain`.
- **HF1.7** `golden_samples/**` — 全部只读
- **HF1.8** `scripts/hf1_path_guard.py` — meta-protection (NEW per AR-2026-04-25-001 §3): the path-guard cannot silently self-modify; every change to it must come through a PR with explicit AR/ADR cover.
- **HF1.9** `.github/workflows/**` — CI enforcement workflows are governance surface (NEW per AR-2026-04-25-001 §3): a silent change to CI bypasses every gate.

**PR-protected zone** (NOT HF1 hard-stop; relies on branch protection per ADR-013 + mandatory Codex M1 trigger per §T2 above):

- `docs/adr/**` — ADR text
- `docs/governance/**` — governance docs
- `docs/failure_patterns/**` — FailurePattern entries

**Why the split (per AR-2026-04-25-001 §3):** ADR-011 v1 placed `docs/adr/`/`docs/governance/` into HF1 hard-stop. But every ADR amendment touched `docs/adr/`, creating a chicken-egg recovery clause — normal governance work was always HF1-overridden. Option 1 (status quo) trained T1 to ignore HF1 alarms; Option 2 (carve-out subdirectory) was safety theater; Option 3 (drop from HF1) was honest. T0 chose Option 3: governance text gets PR review + branch protection + mandatory Codex, NOT pre-commit hard-stop. HF1 hard-stop now means *"you cannot silently mutate execution truth"*; PR-protected zone means *"you cannot silently mutate governance text"*. Two different surfaces, two different gates.

| ID  | Trigger | Detection (现状 / 目标) | Recovery |
|-----|---------|------------------------|----------|
| HF1 | Diff 触及 HF1 hard-stop zone (HF1.1-HF1.9) — PR-protected zone NOT included | **HF1 hard-stop**: pre-commit `scripts/hf1_path_guard.py` (FF-06 ✅) + CI ported version pending; **PR-protected zone**: branch protection (ADR-013) + mandatory Codex M1 (§T2 amended) | HF1 hard-stop: 立即 `git reset --soft`，先开 ADR / 申请 Gate (or `HF1_GUARD_OVERRIDE='<reason>'` for emergencies, audited at PR review). PR-protected zone: regular PR + Codex pre-merge required. |
| HF2 | 单会话 drift > 5 turns / 40k tokens / 3 files / 500 LOC 且未拆分 subagent | T1 自检 + claude-hud 计数（手动） | Calibration Mode 期内可附 ≤30 字理由继续；Calibration Mode 关闭后强制 spawn subagent，否则停手（关闭判据见 §Calibration Mode，与日历无关） |
| HF3 | 新增 sample 无 golden-standard 引用 | `scripts/validate_golden_samples.py` + `golden-samples-validation` CI（FF-08） | 标记 `insufficient_evidence`，不进入回归集 |
| HF4 | Artifact 落入 Decisions DB 但 Notion Handoff 缺失 | **现状**：Notion sync 脚本输出对账 + 人工核对；**目标**：notion_sync.py 端到端 diff 守卫（已部分实现，contract 迁移 in-flight on `feature/AI-FEA-S2.1-02-notion-sync-contract-align`） | 回滚 Decisions 记录；补 Handoff 后重发 |
| HF5 | Codex verify 结论与 repo 真值不一致 | trusted-main `trailer-check` CI + `scripts/check_commit_trailers.py`（FF-07 ✅） | T0 Gate 召回；以 repo 为准修 Notion / Codex 上下文 |

### Enforcement Maturity (post-FF-06, post-AR-2026-04-25-001)

ADR-011 v1 把 HF1/HF5 的 Detection 写成既成事实是 **过度声明** — Codex R1 BLOCKING #1 正确指出。当前真实状态如下（2026-04-25 post-FF-06 amendment cycle）：

| HF rule | Detection layer | Status |
|---|---|---|
| **HF1 (hard-stop zone)** | pre-commit `scripts/hf1_path_guard.py` reads `git diff --cached --name-status -z` (covers renames + deletes). Script also supports CI invocation via `--from-diff <ref>` mode (pure function ready); workflow integration ports the call into `.github/workflows/ci.yml`. | pre-commit ✅ **landed in FF-06 (PR #22, commit `ac98fc3`)**. CI port pending in **ADR-013** (T0 §2 placed CI status check under ADR-013 alongside branch protection). The `--from-diff` script mode lands in this AR-2026-04-25-001 amendment cycle so ADR-013 can wire it without code change. |
| **HF1 (PR-protected zone)** | branch protection (per ADR-013 — pending) + mandatory Codex M1 trigger (per amended §T2) | ADR-013 in flight; Codex M1 active immediately upon AR-2026-04-25-001 ratification |
| HF2 (subagent split) | T1 self-check + `claude-hud` token counter + `reports/hf2_calibration.md` log | honor-system, calibration window open until close-out criteria met (per §Calibration Mode; no calendar deadline per AR-2026-05-03-001) |
| HF3 (sample registry) | `scripts/validate_golden_samples.py` validates signed `GS-###` registry metadata; `.github/workflows/golden-samples-validation.yml` runs it from trusted `main` | FF-08 lands this automation and adds the check to ADR-013 branch protection |
| HF4 (Notion handoff) | `notion_sync.py` diff guard partial; manual reconciliation | honor-system + partial automation; in-flight on `feature/AI-FEA-S2.1-02-notion-sync-contract-align` |
| HF5 (Codex verify) | trusted-main `trailer-check` workflow + `scripts/check_commit_trailers.py` | FF-07 landed via PR #129; branch protection now requires `trailer-check` |

**Tracking tasks (FF-06/07 landed; FF-08/09 remaining):**

- **FF-06** **partially done** — pre-commit hook ✅ landed (PR #22, commit `ac98fc3`, R1+R2 Codex APPROVE); script `--from-diff` mode ✅ landed (this AR-2026-04-25-001 amendment cycle); CI workflow integration **pending ADR-013** (T0 §2 placed CI status check under ADR-013)
- **FF-07** **done** — trusted-main commit trailer workflow + validator landed in PR #129 and branch protection requires `trailer-check`.
- **FF-08**: `golden_samples/<id>` registry schema 校验（HF3 detection automation）— lands `scripts/validate_golden_samples.py`, `.github/workflows/golden-samples-validation.yml`, and ADR-013 branch-protection context `golden-samples-validation`. **Hard prerequisite**: must merge before `Phase_2_Gate_opened` (per §Calibration Mode definition). **Discipline-only sub-clause (audit, not enforced — per Codex R2 LOW #4)**: PRs SHOULD NOT claim "HF3 automation enforced" in their body until FF-08 lands; same discipline / audit semantics as FF-07's HF5 sub-clause above.
- **FF-09** (README ↔ ADR-011 sync): not on automation path, but normative. **Hard prerequisite**: must merge before `Phase_2_Gate_opened` (per §Calibration Mode definition) to ensure README and ADR-011 are not in conflict at the moment Phase 2 activation is granted.

In summary: **HF1 pre-commit enforcement landed in FF-06; CI enforcement pending ADR-013** (which will wire `scripts/hf1_path_guard.py --from-diff origin/main...HEAD` into `.github/workflows/ci.yml`). HF5 is enforced by FF-07. HF3 is enforced by FF-08 once the validator PR lands and branch protection is updated with `golden-samples-validation`. HF2 is calibration-mode honor-system pending §Calibration Mode close-out (no calendar deadline per AR-2026-05-03-001), then hard-stop. HF4 is partial automation + manual reconciliation.

### Calibration Mode (HF2 解除自相矛盾)

ADR-011 v1 在 §Hard-Floor 表述 "STOP" 同时在 Risks §4 允许 4 周内附理由继续 — Codex R1 SHOULD_FIX #2 正确指出这是矛盾。本节明确：

- **Calibration window** (per AR-2026-05-03-001): **task-completion-driven, no calendar end date**. The window opens at 2026-04-25 (this ADR's first ratification) and **closes when the close-out predicate evaluates true**.

  **Defined Phase 2 Gate state events (used throughout this ADR — per Codex R3 MEDIUM #2 normalization)**:

  - `Phase_2_Gate_queued` ≜ "Phase 2 Web Console activation has been **listed on the T0 Gate queue** (i.e., a request for T0 to open the Phase 2 activation Gate has been entered into the Decisions DB Pending list)". This is the **earlier** event — anyone (typically T1) can file the queue entry; T0 has not yet acted.
  - `Phase_2_Gate_opened` ≜ "T0 has **explicitly opened** the Phase 2 activation Gate by ratifying the queue entry into a Decisions DB approved entry". This is the **later** event — strictly happens after `Phase_2_Gate_queued`. By definition, `Phase_2_Gate_opened ⇒ Phase_2_Gate_queued`.

  These two events form an explicit ordered pair; no other Phase 2 state names ("imminent", "pending", "in flight") are introduced elsewhere in this ADR. The Calibration Mode close-out predicate uses `Phase_2_Gate_queued` (the earlier event) so close-out happens before T0 evaluates Phase 2; the §Enforcement Maturity hard-prerequisite clauses for **FF-08 and FF-09** key on `Phase_2_Gate_opened` (the later event) because they must be MERGED by the time T0 grants Phase 2 activation. **FF-07 is the exception**: it has BOTH the `Phase_2_Gate_opened` prerequisite AND an independent pre-Calibration-close-out requirement, because HF5 enforcement is a precondition for treating any Calibration close-out's audit-trail claim as trustworthy.

  The predicate (in explicit Boolean form):

  `( (reports/hf2_calibration.md_entries ≥ 20  AND  T0_accepted_mini_retro == true)  OR  T0_explicit_close_out == true  OR  Phase_2_Gate_queued == true )`

  where:
  1. **Sample-threshold-AND-retro path**: `reports/hf2_calibration.md` accumulates ≥ 20 entries AND T1 has produced a mini-retro on `reports/hf2_calibration.md` AND human (T0) has accepted it. Both clauses required.
  2. **T0 explicit close-out path**: human (T0) issues an explicit close-out at any time, regardless of sample size.
  3. **Phase-2-Gate-queued anti-drift path**: when `Phase_2_Gate_queued == true`, Calibration Mode **closes immediately** (the predicate evaluates true on this clause alone). Concretely: as soon as a Phase 2 activation request is filed to the Gate queue, T1 must (a) produce the mini-retro from whatever sample exists in `reports/hf2_calibration.md`, (b) submit it as part of the same Gate-queue entry. T0 then evaluates Phase 2 activation and the Calibration close-out as a single bundled decision. This forecloses both the "log never reaches 20" drift and the path-3-vs-prose ambiguity from R2 BLOCKER #1.
- 期内 HF2 触发 = T1 在该 turn 内附 ≤30 字理由 + 在 `reports/hf2_calibration.md` 追加一行；可继续。
- 期后 HF2 触发 = 真 STOP；必须当场 spawn subagent 或停手。
- Calibration window 关闭时，T1 必须基于 `reports/hf2_calibration.md` 提交 mini-retro，**决定是否调阈**或维持 5/40k/3/500。

在 calibration window 内 HF2 是 **soft floor**，期后回归 hard floor。其他 HF 不受此例外影响。

**AR-2026-04-25-001 amendment note (self-pass-rate calibration moved to ADR-012):** ADR-011 v1 inherited RETRO-V61-001's per-PR `external_gate_self_estimated_pass_rate` honor-system. Session 2026-04-25 produced empirical data (5/5 PRs T1 self-rated 80-95%, all hit Codex R1 CHANGES_REQUIRED) showing the honor-system is structurally broken — T1 cannot self-correct mid-session. Per AR-2026-04-25-001 §1 (T0 ratification), the self-pass-rate honor-system is replaced by ADR-012's mechanically-derived ceiling computed from the rolling window of the last 5 PRs' Codex R1 outcomes. **HF2 numerical thresholds (5 turns / 40k tokens / 3 files / 500 LOC) and activity-type split (per amended Subagent rule above) are unchanged by this amendment.** ADR-012 governs the calibration math; ADR-013 governs the branch-protection enforcement surface.

---

## 9 Golden Rules

1. **Truth hierarchy immutable** — Code truth = `github.com/kogamishinyajerry-ops/ai-structure-analysis`; work-control truth = Linear issues; runtime truth = `runs/` + CI artifacts; architecture/control mirror = Notion. When they conflict, git/repo truth wins for code and Linear wins for work state; Notion is patched after the fact.
2. **CalculiX is the only numerical truth source** — 任何"等价求解器"声明必须先经 ADR + Gate。
3. **Every architecture decision lands as ADR immediately** — 沿用本仓库 `docs/adr/ADR-{nnn}-{slug}.md` 轻量约定（不复制 cfd-harness-unified DEC frontmatter）。
4. **Handoffs cannot bypass Notion** — 阶段间交接必须有可点开的 Notion Handoff 页。
5. **No golden-standard → no test** — 没有 GS 引用的样本一律 `insufficient_evidence`，不进 regression lane。
6. **Sessions fully traced** — 每个 commit 带 `Execution-by` trailer；Claude audit evidence uses `Reviewed-by` / PR proof links when applicable.
7. **Schema-first** — Pydantic v2 strict validation per `schemas/`；schema 变更先 ADR、再代码。
8. **Reversibility** — 每个决策必须文档化 rollback 路径（见各 ADR 的 Rollback 节）。
9. **Four-layer architecture** — Control / Execution / Knowledge / Evaluation；import 方向单向：Control 可读全部；Execution 仅依赖 Knowledge；Evaluation 独立于 Execution（不允许反向 import）。

---

## Commit Trailer Convention

所有进入 main 的 commit 必须携带：

```
Execution-by: codex-primary
Codex-verified: <claim-id>@<7-40 hex sha>
Reviewed-by: claude-opus47 <verdict-or-proof-ref>
Linear-Issue: ENG-<id>
```

- `Execution-by` 必填，标明 Codex-primary execution path.
- `Codex-verified` 必填于 HF5 claim-proof path，格式为 `<claim-id>@<7-40 hex sha>`；不得使用 `HEAD` / `<sha>` / `pending` 等可变或占位值.
- `Reviewed-by` 在 M1-M5 或 calibration-mandatory review gates 触发时必填，引用 Claude Opus verdict or proof artifact.
- `Linear-Issue` 必填于 Linear-controlled work，保持 work-control traceability.

---

## Consequences

### Benefits

1. **单一可问责执行路径** — `Execution-by` trailer 让任意 commit 都能反查到唯一的人/模型对账主体。
2. **协调延迟下降** — 三模型 → 单模型，消除"等另一边 review 完才能动"的串行等待。
3. **审计可闭合** — commit trailer + Notion ADR + `runs/` 三件套构成最小可审计单元。
4. **上下文窗口压力解耦** — 1M 主上下文 + subagent 隔离取代"频繁 context reset"，长任务可持续推进。
5. **盲点验证职责清晰** — Codex executes; Claude Opus audits gated packets/diffs without taking over execution.

### Risks

1. **单驱动瓶颈** — 当 Codex 验证不可用（额度耗尽 / 服务异常）时，critical claim 无法获得独立验证；缓解：`cx-auto 20` 多账号自动切换。
2. **Subagent 边界违规成本** — Allowed/Forbidden 描述不准会导致 rollback；缓解：HF1 path-guard 前置（FF-06 automation 落地前依赖人工 review）。
3. **In-flight S2.1-02 collision (watch-item)** — 本 ADR 的首次 Notion sync 可能与 `feature/AI-FEA-S2.1-02-notion-sync-contract-align` 的契约迁移在 Notion DB schema 上撞车。**主 session 须在 commit 前手工核对 FF-01b**（"先验证 S2.1-02 是否已合并；未合并则 ADR-011 的 Notion 同步走旧契约，并在 ADR 里补一条 follow-up 标注"）。FF-01b 实测发现 Decisions DS 实际 schema 与 `notion_sync.register_decision()` 期望字段差距更大（缺 `Branch`/`Session Batch`/`ADR Link` 三项），S2.1-02 的 `Sprint` 添加并未对齐 — 应另开 ADR 修 schema。
4. **HF2 自相矛盾** — 见上方 §Calibration Mode（Codex R1 SHOULD_FIX #2 修复）。期内 soft floor，期后 hard floor。Per AR-2026-05-03-001, the window terminates on completion-criteria satisfaction (see §Calibration Mode), not on a calendar date.
5. **T0 召回延迟** — Gate 是人工触发，深夜事件可能滞留；明确 SLA 由后续 ADR 补（候选 SLA：工作日 4h，周末 24h；本 ADR 不强制）。
6. **Enforcement maturity gap** — HF1/HF5 现阶段是 honor-system（见 §Enforcement Maturity）。在 FF-06/07/08 落地前，治理可信度依赖 T1 自检 + PR review。Codex R1 BLOCKING #1 正确指出该差距；本 ADR 接受并以排期对冲，不靠装作已有 hook 来 over-claim。

---

## Rollback

观察窗口 = 当前 Calibration window（per §Calibration Mode close-out criteria，无日历终止日；AR-2026-05-03-001 修订）。Rollback metrics 在 window 期内累计、close-out 时清零并 archive。若 window 期内出现以下任一（指标已加 denominator 与严重度分层，回应 Codex R1 BLOCKING #2）：

- **Codex verification mismatch rate > 15%**，**且**该周期内累积 verified claim ≥ 20。低于 20 时只记录、不触发 rollback（小样本不可靠）。
- **HF1 hard-stop 触发按区域加权 > 2 weighted points** (covers HF1.1-HF1.9 hard-stop zone per AR-2026-04-25-001 §3 amendment; PR-protected-zone bypass tracked separately below):
  - solver core (`agents/solver.py`, `tools/calculix_driver.py`, `agents/router.py`, `agents/geometry.py`) = **1.0 / 次** — HF1.1-HF1.3
  - schema / toolchain pin (`schemas/sim_state.py`, `tests/test_toolchain_probes.py`, `Dockerfile`, `Makefile`) = **0.5 / 次** — HF1.4-HF1.6
  - golden_samples write (`golden_samples/**`) = **1.0 / 次** — HF1.7
  - meta-protection (`scripts/hf1_path_guard.py`, `.github/workflows/**`) = **0.5 / 次** — HF1.8-HF1.9 (NEW per AR-2026-04-25-001)

  例：solver core 误改 1 次 = 1.0 (未触发)；solver core 误改 2 次 = 2.0 (未触发，临界)；solver core 误改 3 次 = 3.0 (触发)；Makefile 误改 5 次 = 2.5 (触发)；CI workflow 误改 4 次 = 2.0 (临界)。

- **PR-protected zone bypass > 2 incidents per window** — tracks unreviewed direct-pushes to `docs/adr/**`, `docs/governance/**`, `docs/failure_patterns/**` (these are no longer HF1 but their integrity depends on branch protection per ADR-013). Each bypass = **0.3 / 次** for the rollback metric, separate denominator from HF1 hard-stop.
- **HF2 calibration window 关闭后**，HF2 hard-stop 触发频次 > 1 in the **first 10 post-close-out T1 sessions OR PRs to main, whichever is reached first** (rolling check, no calendar). The 10-sample observation **must complete in full**; it does NOT reset on Phase activation Gates (per Codex R2 HIGH #2 — decoupled from Phase 2 activation to prevent self-nullification when path-3 close-out fires concurrently with Phase 2 activation). The window resets ONLY on (a) the 10-sample observation completing without violation (counter zeroed at sample 11), OR (b) T0 explicitly opens a new Calibration window via a Decisions DB entry. Concurrent Phase activations DO NOT reset the rollback observation.

任一触发则升级到 T0 (Opus 4.7) 架构审查，重新评估是否需要引入第二条模型通道（候选：Codex 提升为受限的 main-code 提交者，或重新启用一个只读 review 通道）。Rollback 通过新 ADR (ADR-{nnn}-revoke-011) 形式落地，本 ADR 标记为 Superseded。

**记录责任** — calibration window 内由 T1 在 `reports/hf_audit.md` (rolling log; per AR-2026-05-03-001, no calendar suffix in filename) 累计每条 HF / verified claim 数据；window close-out 时整体 archive 到 `reports/archive/hf_audit_window-NNN.md` 并重置 rolling log. `<NNN>` 命名规则 (per Codex R2 HIGH #3 collision-safe variant):

1. **Counter computation MUST happen against latest `origin/main` at the merge commit that closes the window** — NOT against the local working tree. Formula: `NNN = max({N | reports/archive/hf_audit_window-N.md exists on origin/main as of close-out merge SHA}) + 1`, zero-padded to 3 digits. Concurrent branches each compute against the SAME `origin/main` baseline, but only the first to merge wins; subsequent branches MUST recompute against post-merge `origin/main` and pick a fresh `N` before merge.
2. **T0 is the sole arbiter for ALL three close-out paths** (predicate paths 1 / 2 / 3 per §Calibration Mode), including the Phase-2-Gate-queued path. The close-out commit message MUST cite the T0 ratification reference as a **concrete T0 artifact**: either (a) a Decisions DB entry id (`DEC-T0-YYYY-MM-DD-NNN`), or (b) a linked GitHub PR comment URL where T0 explicitly approved the close-out — `§Risks #5` SLA candidates are NOT a substitute for an actual artifact reference. The ratification reference + the resolved `<NNN>` value MUST appear together in the close-out commit message. **Enforcement note (per Codex R3 HIGH #1 — anti-overclaim correction)**: this is a **discipline contract**, NOT a mechanically enforced one. ADR-013's current branch-protection settings are `required_pull_request_reviews = null` and `enforce_admins = false`, which means the protection script does NOT mechanically gate merges on a T0-signature trailer. **Audit ownership**: T1 must self-audit the close-out commit message AT THE NEXT POST-CLOSE-OUT PR (not later), and append a one-line attestation `closeout-audit: PASS / FAIL` to that PR's body; if FAIL or missing, treat as audit-trail violation, escalate to T0 for retroactive ratification or revert. A future ADR (number TBD) may add a CI status-check that mechanically validates the T0 ratification reference; until then, the next-PR T1 self-audit is the operational detector.
3. **Collision = pre-merge governance defect** (must be detected and resolved BEFORE merge by recomputing `NNN` against post-merge `origin/main`). Post-merge ID collision indicates branch-protection bypass and escalates to T0 immediately for window-naming reconciliation.

FF-06/07/08 落地后转为自动统计。

---

## Routing Comparison

| Aspect | Before (Claude Code single-path) | After (Codex-primary Linear/Symphony) |
|--------|------------------------------|----------------------------------|
| Primary driver | Claude Code CLI (Opus 4.7) | Codex |
| Work-control truth | Notion / repo-side snapshots | Linear issues |
| Code truth | GitHub/repo | GitHub/repo |
| Independent review | Codex verify-only | Local Claude Opus reviewer/auditor |
| Architecture mirror | Notion as process SSOT | Notion as mirror after Linear/repo truth |
| Commit accountability | `Execution-by: claude-code-opus47` + optional `Codex-verified` | `Execution-by: codex-primary` + `Reviewed-by: claude-opus47` when gated + `Linear-Issue` |

---

## Known Gaps (Codex R1 NICE_TO_HAVE 回应 — 显式声明非默认存在)

以下治理元素 ADR-011 没有规定，且仓库当前不具备。未来 ADR 必须补：

1. **`main` 分支保护** — GitHub 端的 required-reviews / required-status-checks / disallow-force-push 设置；当前仅 `README.md:81` 声明 "all code via PR"，不可执法。**Tracked: ADR-013 (branch protection — sibling to this amendment cycle, lands separately per AR-2026-04-25-001 §2).**
2. **PR review 状态机** — 本 ADR 没有规定 PR 必须经过 (a) Codex post-commit review (b) reviewer 至少 1 人 (c) 所有 conversation resolved 才能 merge 的状态流。**Tracked: ADR-013 §3 (solo-maintainer self-approval protocol, per AR-2026-04-25-001 §2).**
3. **Subagent 失败回滚 SOP** — 当 subagent 越界（HF1）、超时、或返回 INSUFFICIENT_EVIDENCE 时，T1 应当 (a) 不引用 subagent 输出 (b) 落 `reports/subagent_failures/` 记录 (c) 决定降级路径。本 ADR 没有具体 SOP。**Tracked: future ADR (number TBD; was "ADR-013 候选" in v1 but ADR-013 has been reassigned to branch protection per AR-2026-04-25-001).**
4. **FailurePattern 与 ADR 的 promotion 路径** — FF-02 已 land 到 main (PR #18, commit `77e6813`)。`docs/failure_patterns/README.md` 与 `FP-001/002/003` 现已在 main。FP → ADR 的 promotion 规则（什么时候一个 FP 必须升级为 ADR）未规定。**Tracked: future ADR (number TBD; was "与 ADR-012 合并" in v1 but ADR-012 has been reassigned to calibration cap per AR-2026-04-25-001).**

**AR-2026-04-25-001 amendment note on ADR numbering**: T0 ratified ADR-012 = calibration cap and ADR-013 = branch protection. The "ADR-012 候选" / "ADR-013 候选" reservations T1 made in ADR-011 v1 for *other* work (branch protection / FP→ADR promotion / Subagent failure SOP) were **incompatible with T0's reassignment**. Items #1 and #2 above scope-match ADR-013 and have been redirected; items #3 and #4 use "future ADR (number TBD)" per the same FP-001/002/003 fix pattern (avoid pre-reserving ADR IDs). FP-001/002/003 in `docs/failure_patterns/` likewise refer to "future ADR (number TBD)" instead of ADR-012/013.

## Glossary (外部工具引用 — repo 内不打包)

- **`cx-auto`** — `~/.local/bin/cx-auto`，本地多账号 Codex 额度切换脚本（`cx-auto 20` = 当前账号配额 < 20% 时自动切换到剩余最多的账号）。脚本不在 repo 内，是开发者本地依赖；CI 不依赖该脚本。`Risks #1` 的"`cx-auto 20` 多账号自动切换"指此工具。
- **`claude-hud`** — Claude Code CLI 的状态栏组件，显示实时 token / context 使用率。HF2 表中"claude-hud 计数"指开发者目测该状态栏判断是否逼近 5/40k/3/500 阈值。同样是本地依赖，无 repo 内 vendoring。
- 两者都是 honor-system 的辅助：当外部工具不可用时，T1 仍需手工自检 HF2 / 自切 Codex 账号；缺失外部工具不是 HF 触发，但也不能用作"算不到所以未触发"的借口。

## Cross-References

- Phase 1.5 Foundation-Freeze 任务集 **FF-01 .. FF-05**；本 ADR = **FF-01**（governance baseline）。R2 修订引入 **FF-06/07/08** automation 跟踪与 **R2 retro 任务**。
- In-flight branch **`feature/AI-FEA-S2.1-02-notion-sync-contract-align`** — 本 ADR 不阻塞，独立分支落地；FF-01b 实测发现 Decisions DS schema 缺 `Branch`/`Session Batch`/`ADR Link`，与 S2.1-02 的 `Sprint` 添加方向不一致，应另开 ADR 修 schema。
- **GS-001 / GS-002 / GS-003** deviation attribution = **FF-02**。Subagent 完成于独立分支 `feature/AI-FEA-FF-02-failure-patterns` (commit `020f2d3`，4 个新文件：`docs/failure_patterns/README.md` + `FP-001/002/003`)。本分支不携带这些文件；两个分支独立合入 main 后才能在 main 上同时观察到。FP 提议 GS 状态全部 → `insufficient_evidence`，是 Phase 2 Web Console 激活的硬前置之一。
- 本仓库 `README.md:79-86` 的 5 development rules 与本 ADR 的 9 Golden Rules **部分重叠** (Rules #1, #4 大致对应 README #1, #2; Rules #3, #5 对应 README #3, #5; Rules #2, #6, #7, #8, #9 在 README 中不存在或仅隐含)。后续 README 与 ADR 冲突时以 ADR 为准；同时跟踪 README 同步 (FF-09 候选)。
- `docs/architecture.md:7` 与 `docs/well_harness_architecture.md:23` 描述了系统组件与闭环，但 **未定义到可执法的 four-layer import 边界**。本 ADR 第 9 条 Golden Rule 是首次声明该边界 — 实际 lint enforcement (e.g. `import-linter`) 跟踪 future ADR (number TBD; was "ADR-012 候选" in v1, reassigned per AR-2026-04-25-001).
- Notion 控制塔页：[AI StructureAnalysis 项目中枢](https://www.notion.so/AI-StructureAnalysis-345c68942bed80f6a092c9c2b3d3f5b9) (root_page_id `345c68942bed80f6a092c9c2b3d3f5b9`，已与 `config/well_harness_control_plane.yaml` 对齐)。
- **Codex R1 review report** — `reports/codex_tool_reports/adr_011_r1_review.md` (CHANGES_REQUIRED, addressed in R2 amendment)。
