# ADR-018: Electron Packaging Strategy — Defer Until A Non-Dev Evaluator

- **Status:** Draft (parallel to ADR-014, ADR-015, ADR-016, ADR-017)
- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — human-confirmed
- **Date:** 2026-04-28
- **Related Phase:** RFC-001 W5 — engineer-wedge demo shell
- **Branch:** `refactor/RFC-001-W5d-ADR-018-packaging-strategy`
- **Companion ADRs (Draft, parallel):** ADR-014 (WS event bus), ADR-015 (workbench → agent RPC), ADR-016 (`.frd` → `.vtu` + result viz), ADR-017 (RAG facade)

---

## Context

W5 (PRs #83–#86) shipped an Electron shell that wraps the `report-cli` subprocess. The shell currently runs in **dev mode only**:

```
pip install -e .
cd frontend
npm run electron:build
npx electron dist-electron/main.js
```

This is enough for the **engineer-wedge demo** the RFC-001 §3 wedge promises (an engineer with a dev environment runs a structural-strength report and gets a signed `.docx` in 30 minutes). It is **not** enough for a non-engineer end-user — they have no Python venv, no `pip`, no `npm`.

A first instinct is to immediately produce signed `.dmg` / `.exe` installers via `electron-builder`. The cost of that path is real and largely invisible from the wedge's vantage point. This ADR pins the decision to **defer packaging** until we have a paying customer or a confirmed pilot, and documents the reasoning so a later contributor doesn't relitigate it.

---

## Decision

**Packaging is out of scope for the W5 engineer-wedge.**

- The W5 deliverable is **dev-mode runnability** — `pip install -e .` + `npm run electron:build` + `npx electron …` produces a working shell on macOS, Windows, and Linux.
- `electron-builder`, `dmg-license`, code-signing certificates, auto-update infrastructure, and bundled-Python decisions are **deferred to W5d** as a separate, scoped piece of work, **gated on the first evaluator who must self-run the demo without Python or Node already installed**. (A paying customer or confirmed pilot will likely trip this gate; an engineer-led pilot will not. The trigger is the *capability gap*, not the commercial milestone — phrasing it commercially risks packaging too early for an engineer-led pilot or too late for a non-dev evaluator.)
- Until that gate, the demo audience is engineers (RFC-001 §3 wedge audience, see `docs/RFC-001-strategic-pivot-and-mvp.md:24`). They can install Python and Node. They are not the constraint.

When the gate trips, W5d kicks off with a fresh ADR-019 covering the specific packaging decisions below.

---

## Why defer

1. **Wedge-shaped scope.** The RFC-001 wedge is "engineer signs DOCX in 30 minutes". An engineer running `pip install -e .` is inside the wedge. A non-engineer trying to run a `.dmg` is a different audience entirely — packaging is the *next* product, not the wedge.

2. **Bundled Python is not free.** Even with `python-build-standalone`, the bundle adds 60-100 MB to the artifact, requires platform-specific signing, and changes the troubleshooting story (engineers can't `pip install` an extra wheel into a frozen interpreter). `report-cli --doctor` (PR #86) was scoped specifically against the unbundled-Python world.

3. **Code signing has a calendar cost, not a code cost.** Apple Developer ID enrollment, Windows Authenticode certificate procurement, notarization workflows — these are weeks of clock time even with everything done correctly. Doing them before we know whether the demo lands is paying setup cost on a path we may not take.

4. **Auto-update infrastructure has an ongoing cost.** Hosting `electron-builder`'s update feed, signing each release, notarizing each release on macOS — every release becomes a multi-step process. Pre-customer, the right shape is a manual `git pull && npm run electron:build`.

5. **The unbundled path is itself a feature for the wedge.** Engineers who run the wedge often want to debug into the Python — set breakpoints in `app.services.report.draft`, edit `templates.py`, etc. A frozen bundled interpreter would make this strictly worse.

---

## What this means concretely

For the duration of "before first customer":

- **No `electron-builder` config in this PR.** No `build:` block in `frontend/package.json`. No `dmg-license`, no `electron-builder.yml`, no `notarize.js`.
- **No bundled Python.** `report-cli` is assumed to be on `PATH`, installed via `pip install -e .` from a venv the engineer manages. The Electron shell's spawn-failure hint (PR #86) already says exactly that.
- **No code-signing certificate procurement.** No Apple Developer enrollment, no Windows Authenticode purchase.
- **No auto-update mechanism.** Users update by `git pull && npm run electron:build` from the repo. Acceptable for engineers, unacceptable for end-users — when end-users matter we revisit this.

The README (or W5 handoff) **must** document the dev-mode launch sequence. PR #84's `--doctor` install probe and the spawn-failure hint already cover the broken-install path; what's missing is a positive walkthrough. That's a doc-only follow-up, not part of this ADR.

---

## What W5d will need to decide (when it kicks off)

This list is intentional — it documents what's *not* decided here, so the W5d author starts from a clean slate.

1. **Bundled Python: yes / no.** `python-build-standalone` (small, well-supported) vs assume a system Python (smaller download, more fragile). Probably yes when end-users matter; defer the decision.
2. **`report-cli` discovery.** If we bundle Python, the shell's `spawn("report-cli", ...)` call needs to point at the bundled interpreter, not the system one. Likely a packaged-mode `app.getPath("module")` check in `main.ts`.
3. **Code-signing strategy.** Apple Developer ID + notarization for macOS, Authenticode for Windows. Linux: probably AppImage unsigned + a sha256 manifest.
4. **Update mechanism.** Manual download, `electron-builder` auto-updater, or in-app "check for updates" link. Manual is fine for the first paying customer; auto-update is fine when there are >1.
5. **Distribution channel.** Direct download from a CDN, or a customer-facing landing page. Probably the latter; out of scope for this ADR either way.
6. **Bundle the demo `golden_samples/GS-001`.** The current dev-mode demo button (#84) finds the sample by walking up from `__dirname`. Packaged mode needs an `extraResources` entry. Trivial when we get there.
7. **Telemetry / crash reporting.** None today. Adding any requires a privacy review separate from packaging.
8. **Packaged resource layout.** Where do bundled Python, `golden_samples/`, and `dist-electron/` live in the packaged app's `resources/` tree? `electron-builder` defaults are reasonable but need to match `main.ts`'s discovery code.
9. **`asar` vs unpacked.** `asar` packs JS/HTML/CSS into a single archive — fast app launch, but can't directly execute bundled binaries from inside it. Bundled Python interpreter and any C extensions must go in `asarUnpack`. Decide which paths are unpacked, document the rule.
10. **Child process `cwd` / env contract.** In packaged mode, the renderer's spawn must set `cwd` and `env` explicitly (don't inherit from however the user launched the app). Decide what `report-cli` sees as its working directory and which env vars are passed through (e.g., `PYTHONPATH`, `PATH` derivation, locale).
11. **Architecture matrix.** macOS arm64 + x64 (universal vs separate builds), Windows x64, Linux x64. ARM Linux probably out of scope. Decide what we ship for each and how CI builds them.
12. **Packaged-mode `--doctor`.** PR #86's install probe is meaningful in dev mode (engineer can `pip install` a missing wheel). In packaged mode, "missing numpy" means the bundle itself is broken; the diagnostic message should reflect that — "report this as a bug" rather than "pip install".

---

## Trade-offs

**What we're accepting.** A non-engineer cannot run the demo. This blocks any sales-motion or pilot that doesn't have an engineer in the loop. The wedge audience does not include non-engineers, so this is a clean trade-off — but it's a trade-off worth naming.

**What we're not accepting.** The wedge audience cannot run the demo. We're explicitly *not* taking that hit — `pip install -e . && npm run electron:build && npx electron …` is *coded to work* on the three major desktop OSes; tests pass and the renderer compiles clean. Whether it actually behaves end-to-end on each OS is a per-OS human-smoke-test claim, not a paper-tested one (see Success Criteria below).

**W5 does not block packaging.** Picking up packaging later does NOT mean a single one-line spawn-target swap. The current shell makes three repo-relative assumptions that W5d will need to revisit, in addition to the spawn target:

1. **Command resolution.** `spawn("report-cli", argv)` (`frontend/electron/main.ts:183`) inherits the launching shell's `PATH`. Packaged mode breaks that — the bundled `report-cli` is at a path the OS shell doesn't know about.
2. **Sample/resource lookup.** `get-demo-frd` walks up from `__dirname` and `process.cwd()` (`main.ts:127-139`) to find `golden_samples/GS-001/gs001_result.frd`. Packaged mode flattens the tree — the sample lives under `resources/extraResources/` instead of two levels above the compiled JS.
3. **Spawn-failure diagnostics.** The current error hint (`main.ts:200-205`) tells the engineer to `pip install -e .`. In packaged mode, that's not a remediation — the bundle is either correct or broken; the message has to change.

What W5 explicitly *does* preserve: the IPC surface between renderer and main is small (`preload.ts` exposes 7 methods), and the renderer makes no filesystem assumptions of its own. So W5d's work is concentrated in `main.ts` (command resolution + cwd/env + sample lookup + diagnostics rewrite) plus a fresh `electron-builder` config — none of it requires reshaping the renderer or the Python CLI.

---

## Success criteria

The criteria are split between **paper-passing** (PR diff + tests + lint) and **human-smoked** (a person opened the app on a specific OS and clicked the buttons). The two are *not* the same thing — paper-passing means "the code says this should work"; human-smoked means "I watched it work on macOS / Windows / Linux on this date".

**Paper-passing today (PRs #83-#86):**

1. ✅ `pip install -e .` from repo root succeeds
2. ✅ `cd frontend && npm run electron:build` succeeds (tsc + postbuild clean on macOS dev environment)
3. ✅ Renderer compiles, IPC surface typed end-to-end, lints clean
4. ✅ `report-cli --doctor` returns 0 in a healthy venv and 3 with focused diagnostics when a dep is missing or BROKEN — covered by 9 tests in `tests/test_report_cli_doctor.py`
5. ✅ Structured violation panel renders input refusals as `<li>` items (not stdout dump) — covered by code review (PR #85), no automated UI test
6. ✅ Spawn-failure hint upgraded to point at `--doctor` (PR #86)

**Human-smoked — NOT yet covered:**

7. ⬜ `npx electron dist-electron/main.js` opens the window on macOS, Windows, *and* Linux. Tests pass and tsc compiles on macOS dev only; the other two OSes are an inferred-but-unverified claim.
8. ⬜ Clicking "Run GS-001 demo" actually produces a valid `.docx` on disk in <30 s. The CLI test (`backend/tests/test_report_cli.py`) verifies this end-to-end *via Python*, not *via Electron IPC clicking through the renderer*. The integration step is unverified.
9. ⬜ The violation panel actually appears in the rendered window when an empty form is submitted. PR #85 verifies via code path; the visual-rendering claim is unverified.

(7)-(9) are the gates that actually close W5. They are by construction blocked on a human running the binary, not on more code.

---

## Open questions

No additional open questions beyond the W5d decision list above (items 1-12). Listing them prematurely would be design-by-anxiety; the W5d author will face them when packaging restarts.
