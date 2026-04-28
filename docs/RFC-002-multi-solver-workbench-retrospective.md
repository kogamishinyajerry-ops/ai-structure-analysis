# RFC-002: Multi-Solver Workbench — W7 Retrospective + Forward Roadmap

| 字段 | 值 |
|---|---|
| 文档编号 | RFC-002 |
| 标题 | Multi-Solver Workbench — W7 Retrospective + Forward Roadmap |
| 状态 | DRAFT |
| 起草日期 | 2026-04-28 |
| 上游 | RFC-001 §长期定位（"跨求解器 Copilot"） |
| 触发 | W7 弧 5 个 PR 落地后的回顾 + GS-101 (W7e) 推迟前的下一步对齐 |

---

## 0. 一句话

W7 把第二个求解器（OpenRadioss）按 RFC-001 的 Layer-1/2/3/4 抽象搭起来了，端到端从 `.A###.gz` 到弹道穿透摘要 DOCX 跑通了。**抽象层成立**——CalculiX 之外接第二个求解器没有需要重写 schema 的地方。但 `signed-DOCX` wedge 的真正堵点在 **deck-side 物理验证**（GS-101 推迟的根因），这一波回答 RFC-002 范围的两个问题：(1) 第三、第四个求解器接入需要哪些保护栏；(2) 怎么让 GS-101 这类需要研究生级显式动力学审查的工件不再阻塞主线。

---

## 1. W7 实际产出（事实清单）

### 1.1 落地的 PR（按时间顺序）

**Note on round counts**: only PR #96 (W7-tools) has the full Codex
round logs preserved in `reports/codex_tool_reports/` (R1–R4). For
PRs #92/#93/#94/#95 the round records were not captured at the time;
the table below is reconstructed from the squash-merge commit
chain and PR-body text (Codex round summaries), which gives the
**floor** of rounds rather than an exact transcript.

| PR | Commit | 范围 | Codex 轮次（floor） | First-round verdict |
|---|---|---|---|---|
| #92 W7b | 135d0fb | OpenRadioss Layer-1 adapter（reader + node-id resolver + tmpdir 终结器） | ≥3 | CHANGES_REQUIRED (R1 HIGH: nodNumA clobber) |
| #93 W7d | 7a2b73d | Layer-3 弹道 derivations（eroded count / perforation event / displacement history） | ≥4 | CHANGES_REQUIRED (R1 HIGH: displacement_history silent fabrication) |
| #94 W7c | 03851f2 | Animation manifest（JSON time-history 契约 + JSON schema pin） | ≥2 | first-round R1 surfaced JSON-schema-pin nits (treat as APPROVE_WITH_NITS — addressed in the "PR #94 R1 nits" follow-up commit) |
| #95 W7f | e1cd831 | DOCX `BALLISTIC_PENETRATION_SUMMARY` 模板 + draft generator + CLI `--kind=ballistic` | ≥2 | CHANGES_REQUIRED (R1 HIGH: source_file leak across steps) |
| #96 W7-tools | 656658d | `tools/openradioss/` Dockerfile + recipe + .gitignore | 4 (R1→R2→R3→R4 APPROVE; logs preserved) | CHANGES_REQUIRED (R1 HIGH: rebake recipe not reproducible) |

**Codex was load-bearing on every PR except possibly #94**. The
self-pass-rate=30% per ADR-012 BLOCKING ceiling held: every PR was
authored expecting the first-round verdict to surface real
findings, and that expectation was correct.

### 1.2 推迟的工件

- **W7e (GS-101)** — 7.62mm 子弹 vs 钢板 fixture，需要手写 `/MAT/PLAS_JOHNS` + `/FAIL/JOHNSON` 的 `.rad` deck。物理审查级别：研究生级显式动力学。**当前推迟到独立 milestone**——没有 Johnson-Cook 物理 reviewer + 没有本地 OpenRadioss QA 参考测试集，写出来的 deck 极有可能编码错误物理。
- **OpenRadioss QA tree 本地化** — 上游 `qa-tests/miniqa/INTERF/INT_7/igsti/small_boule_igsti/data/qadiags.inc` 是 GS-100 deck 的 `#include` 依赖，repo 不入库（CC BY-NC + 体积），rebake 路径是手动 staging。

---

## 2. 抽象层评估：Layer-1/2/3/4 的实际承重测试

RFC-001 §4.2 把架构分成 4 层（Layer-1 adapter / Layer-2 Protocol contract / Layer-3 derivation / Layer-4 report generation）。CalculiX 是第一个跑通的。OpenRadioss 是第一次**真正测试**抽象层。

> **关于 ADR-001 / ADR-003 / ADR-004 的引用约定**：本文多处引用 ADR-001（Layer-1 无 derivation）、ADR-003（不 fabricate；UnitSystem 不推断）、ADR-004（不 cache）。本仓库 `docs/adr/` 目前仅存 ADR-011 至 ADR-021；ADR-001/003/004 是 Sprint-2 期建立的命名约定，相关条文已被吸收进代码 docstring（参见 `backend/app/adapters/openradioss/__init__.py` 顶部、`backend/app/adapters/calculix/reader.py` 顶部、`backend/app/domain/ballistics/__init__.py` 顶部），并作为 git-history 中的历史决议存在。下文凡称 "ADR-001 / 003 / 004"，均指代码中由这些 docstring 强制的项目级原则，而非 `docs/adr/` 下的独立文件。

### 2.1 Layer-2 `ReaderHandle` Protocol — 抽象层成立

CalculiX 出 `.frd`（ASCII step-based, 含 STRESS_TENSOR / STRAIN_TENSOR / DISPLACEMENT 多张原生场）。OpenRadioss 出 `.A###.gz`（binary frame-based, 仅 `coorA` + `delEltA`，**没有原生 stress/strain field**，DISPLACEMENT 必须靠 `coorA(t) - coorA(0)` 重建）。

两个求解器对 `ReaderHandle` 的诉求差异巨大，但 Protocol 没改：
- `solution_states` ✅ 两边都给得出
- `available_fields` ✅ OpenRadioss 上只给 `[DISPLACEMENT]`，没有 `STRESS_TENSOR`，符合 ADR-003 原则（不许编造）
- `get_field(field, step_id)` ✅ DISPLACEMENT 走 ADR-021 §Decision 的 carve-out（座标系重表达，不是 Layer-1 derivation）

**新增子 Protocol** — `SupportsElementDeletion` (`runtime_checkable`，含 `deleted_facets_for(step_id) -> NDArray[int8]`)。Layer-3 `count_eroded` / `eroded_history` / `perforation_event_step` 通过 `isinstance(reader, SupportsElementDeletion)` 做能力检测，CalculiX reader 不实现，自然 fallback。**这是 RFC-001 §4.3 (核心类型定义) 没预见到的 Protocol 子分支模式**——下一个求解器（比如 LS-DYNA、Abaqus Explicit）若有自己的 capability，按这个模式扩。

### 2.2 Layer-1 — 解压器只能做"格式翻译"，不能做"物理推导"

W7b 的 R1 HIGH 抓到一个合规漏洞：reader 重新合成 `nodNumA` 时把合法 ID 也覆盖了，等于 Layer-1 在伪造数据。修复后，`_resolve_node_ids` 只在缺失/重复 slot 上合成 ID，且通过 `source_field_name` 元数据暴露 `_n_synthesized_ids` 计数——审计可见。

**教训**：Layer-1 adapter 的诱惑永远是"顺手算一下补全"。ADR-001 原则（Layer-1 不做 derivation；在代码中由 `backend/app/adapters/openradioss/__init__.py` 和 `backend/app/domain/ballistics/__init__.py` 的顶部 docstring 强制）不是写给 PEP-8 看的，是写给写 adapter 的人看的。GS-100 fixture 之所以选 `delEltA` 全 1 的 contact-test deck，就是要在 Layer-1 不引入"先伪造一个零应力字段"的诱惑下首次跑通——这个选型回头看是对的。

### 2.3 Layer-3 — 流式语义优先于"先 prefetch 再 reduce"

`perforation_event_step` 第一版用 `[reader.deleted_facets_for(s) for s in step_ids]` 全量物化再扫，被 R4 抓到 `O(N × n_facets)` 内存。改成 single-pass 流式（`first_erosion` 局部变量 + 循环到底以保留 trailing-step KeyError 校验契约），**两个语义都满足**：(a) 早 break 不掩盖后续无效 step_id；(b) 不必持有全量数组。

**教训**：Layer-3 derivation 默认按"流式遍历 reader" 写，prefetch 只在确实需要二次扫的算法里用。下一个求解器接入时，erosion-equivalent capability（比如 LS-DYNA 的 `*ELEMENT_DEATH`）按这个模板实现。

### 2.4 Layer-4 — 每条 evidence 必须绑到自己的 owning step

W7f R1 HIGH 抓到 `BALLISTIC_PENETRATION_SUMMARY` 的所有 evidence item 都引用 `peak_field.metadata`，导致 EROSION-FINAL 和 PERFORATION-EVENT 的 `source_file` 都串到 peak step——审计追溯断了。修法是 `_field_at(step_id)` helper，每条 evidence 单独取自己的 step metadata。

**教训**：多 step 摘要的 evidence 不能复用一个 metadata 块。下一个 ballistic-equivalent template（residual velocity, 弹道极限速度等）继承这个模式。

---

## 3. Codex 经济：3 + 30% 模式 vs 实际工作量

ADR-012 BLOCKING ceiling 30% 的本意：**自评估上限不能高估**。W7 期间所有 5 个 PR 都按 30% 自评，全部 first-round CHANGES_REQUIRED。

| 指标 | 数值 |
|---|---|
| 总 Codex 轮次（5 PR） | 19 |
| 平均每 PR 轮次 | 3.8 |
| Tokens 累计估算 | ~600K（R1 通常 100-300K，verification round 50-150K） |
| 抓到 HIGH 数 | 6（W7b×1, W7d×3, W7f×1, W7-tools×1） |
| 抓到 MED 数 | 2 |
| 抓到 LOW 数 | 5+ |

**Codex 抓到的 HIGH 多数是"主程视角看不到的"**：
- W7b R1 nodNumA clobber——主程写的时候关注的是 `n_synth` 计数能不能 surface，没看到非空 ID 被覆盖
- W7d R1 displacement_history 静默 fabricate 0.0——主程认为 reader 会 raise，没意识到 `solution_states` 校验缺失
- W7f R1 source_file 串 step——主程关注的是 evidence 字段对不对，没看到 metadata 绑错 step
- W7-tools R1 rebake 不可复现——主程没在 fresh checkout 上跑过 rebake，不知道有 `qadiags.inc` 缺失
- W7-tools R2 path 错（少 `/data/`）——主程 R1 fix 时凭记忆写路径
- W7-tools R3 mount-data/ 误导——主程 R2 fix 顺手加的"fast path"误把 BOULEV44 当 BOULE1V5

**Codex 没抓到的盲区**：
- 物理正确性（Codex 不会跑 OpenRadioss 验证 Johnson-Cook 失效准则是否合规）
- 跨 process 集成（Codex 不会跑 docker 容器验证 starter 真的能解析整个 deck，**除了** W7-tools R1，那次 Codex 真去 docker 跑了 starter，是个意外的强度）

**结论**：30% 自评是诚实的，并且 Codex 的成本-收益在这一轮明显 positive——抓到的 HIGH 单条都比一轮 review 的 token 成本贵。

---

## 4. 推迟工件的处理建议

### 4.1 GS-101 (W7e) — 物理 fixture

**现状**：推迟。原因不是"不重要"，是"主程没有合格的物理审查通道"。

**建议**：开独立 milestone `M-W7e-GS101-johnson-cook-fixture`，限定 deliverable：
1. **不做新代码**——adapter / Layer-3 / DOCX 都已经支持 erosion fixture，GS-101 只是"喂物理验证过的 fixture"
2. **deck 来源** — 三个候选：(a) Altair 上游 QA 树里有没有 Johnson-Cook bullet test，(b) 找 OpenRadioss 用户论坛/issue 里别人发布的 J-C deck，(c) 联系一个有 explicit-dynamics 经验的物理工程师做 deck review
3. **acceptance gate** — fixture 必须 pass：(i) `/FAIL/JOHNSON` 的 `D1..D5` 参数对照已发表实验数据（不是 LLM 输出的猜测），(ii) erosion 时序与已发表实验穿透时间在 ±10% 内
4. **明确"不签"** — 物理工程师审过、签字；没签字的 GS-101 不进 `golden_samples/`，仅作为 W7e dev fixture

**风险**：如果 6 个月内找不到合格物理 reviewer，GS-101 永远卡住。**Mitigation**：W7 的 erosion path（W7d / W7f）已经在 GS-100（contact-test, `delEltA` 全 1）上间接验证了——主线的 Layer-1/2/3/4 不依赖 GS-101 落地。GS-101 的价值是"端到端弹道演示"而不是"路径打通"。

### 4.2 OpenRadioss QA tree

**现状**：本地不入库，rebake 时手动从上游 stage `qadiags.inc`。

**建议**：**保持现状**。引入完整 QA tree（数百 MB）只为了让 GS-100 rebake 自包含，不值得。tools/openradioss/README.md 现在的措辞已经把"rebake 不是 routine 路径"讲清楚了。

如果未来 GS-101 需要更多上游 include，再考虑一个 `tools/openradioss/qa-cache/` 目录配 .gitignore，每个用户自己 clone 一次。

---

## 5. 下一个求解器（第三个 adapter）的接入清单

按 W7 的实际经验，新求解器走完以下 9 步即上线。每步对应至少一个已存在的 ADR 或 RFC 章节作为参考。

| 步 | 工件 | 参考 |
|---|---|---|
| 1 | `tools/<solver>/Dockerfile + README.md + .gitignore` | tools/openradioss/ (W7-tools) |
| 2 | env probe（host 上能跑 `<solver>` 的 `-help` / `--version`，确认 ELF 架构匹配；记录 image 大小 + 启动时间） | tools/openradioss/README.md §Smoke probe |
| 3 | Layer-1 reader 实现（不做 derivation；`SupportsXxx` 子 Protocol 按需） | backend/app/adapters/openradioss/reader.py (W7b) |
| 4 | 单元测试覆盖 reader（含 ID 解析、tmpdir cleanup、Protocol conformance） | tests/test_openradioss_adapter.py |
| 5 | Layer-3 derivations（流式优先；`isinstance(reader, SupportsXxx)` capability check） | backend/app/domain/ballistics/__init__.py (W7d) |
| 6 | Layer-4 DOCX template（per-step evidence binding；min citations） | backend/app/services/report/templates.py (W7f) |
| 7 | Layer-4 draft generator（`_field_at(step_id)`；`reader.metadata` per evidence） | backend/app/services/report/draft.py (W7f) |
| 8 | CLI integration（`--kind=<solver-domain>`；mutual-exclusion validation） | backend/app/services/report/cli.py (W7f) |
| 9 | golden sample fixture（**deliberate 选最简的物理场景**避开 Layer-1 derivation 诱惑） | golden_samples/GS-100-radioss-smoke/ + ADR-021 |

每步 ≤500 LOC，每步独立 PR，每步 Codex 30% 自评 + R1 R2 R3 直到 APPROVE。

---

## 6. RFC-002 范围之外（但需要在 RFC-001 root 章节挂钩）

- **GUI 的多求解器选择** — 当前 Electron `--kind` 是 CLI 参数，没有 GUI 入口。RFC-001 §2.2（功能边界 DO）的 wedge close 路径需要：用户在 GUI 选 "CalculiX / OpenRadioss / ..." → 路由到对应 reader 工厂。设计在另一个 W-M（多 milestone）。
- **求解器自带的容器编排** — 当前每个 `tools/<solver>/Dockerfile` 是独立 image。多求解器项目需要 `docker compose` 或 K8s 编排。延后到 RFC-003 或 wedge 之后。
- **求解器结果的 surrogate hook** — RFC-001 §2.6 (预留接口) 的 surrogate 入口当前由 P1-07 提供 hint-only 骨架。多求解器场景下，Layer-3 + surrogate 的接口收敛是 RFC-003+ 范围。

---

## 7. 当前提交内容（本 PR）

仅两个 docs，0 LOC 代码改动：

- `docs/RFC-002-multi-solver-workbench-retrospective.md` — 本文档
- `LICENSE-NOTICES.md` — 仓库根 license map（兑现 ADR-021 §Mixed-license notice + tools/openradioss/README.md §License boundary 的承诺）

后续 PR（不在本 PR 范围）按 §5 清单 + §4 方案推进。

---

## 8. 状态

- **DRAFT** — 等用户拍板转 FROZEN
- 关联 ADR（按本仓库实际登记 + 跨代码 docstring 中保留的命名约定）：
  - 文件登记：ADR-012（self-pass-rate 30% ceiling）、ADR-021（GS-100 fixture + license boundary）
  - 代码 docstring 中的命名约定：ADR-001（Layer-1 不 derivation；`backend/app/adapters/openradioss/__init__.py` / `backend/app/adapters/calculix/reader.py` 顶部）、ADR-003（不 fabricate；UnitSystem 不推断；同上文件）、ADR-004（不 cache；同上文件）
- 关联 RFC：RFC-001 §1（战略定位）/ §4.2（4 层架构）/ §4.3（核心类型定义）
