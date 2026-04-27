# ADR-018: Electron Packaging Strategy — Defer Until First Customer

- **Status:** Draft
- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — human-confirmed
- **Date:** 2026-04-28
- **Related Phase:** RFC-001 W5 — engineer-wedge demo shell
- **Branch:** `refactor/RFC-001-W5d-ADR-018-packaging-strategy`
- **Companion ADRs:** ADR-016 (`.frd` → `.vtu` + result viz), ADR-017 (RAG facade)

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
- `electron-builder`, `dmg-license`, code-signing certificates, auto-update infrastructure, and bundled-Python decisions are **deferred to W5d** as a separate, scoped piece of work, **gated on the first paying customer or confirmed pilot**.
- Until that gate, the demo audience is engineers (RFC-001 §3 wedge audience). They can install Python and Node. They are not the constraint.

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

---

## Trade-offs

**What we're accepting.** A non-engineer cannot run the demo. This blocks any sales-motion or pilot that doesn't have an engineer in the loop. The wedge audience does not include non-engineers, so this is a clean trade-off — but it's a trade-off worth naming.

**What we're not accepting.** The wedge audience cannot run the demo. We're explicitly *not* taking that hit — `pip install -e . && npm run electron:build && npx electron …` works on the three major desktop OSes today.

**Reversibility.** Picking up packaging at any later point is straightforward — the Electron shell is already structured around a single `spawn("report-cli", argv)` call (`frontend/electron/main.ts:183`). Swapping the spawn target for a bundled-Python path is a localized change. We are not building anything in W5 that makes packaging harder later.

---

## Success criteria

W5 is "done" when:

1. ✅ `pip install -e .` from repo root succeeds
2. ✅ `cd frontend && npm run electron:build` succeeds (PRs #83-#86 verified)
3. ✅ `npx electron dist-electron/main.js` opens the window with form, kind dropdown, output picker, GS-001 demo button
4. ✅ Clicking "Run GS-001 demo" produces a valid `.docx` on disk in <30 s
5. ✅ Running with broken or missing inputs surfaces a structured violation panel rather than a stdout dump (PR #85)
6. ✅ When `report-cli` is missing, the spawn-failure hint suggests `report-cli --doctor` (PR #86) and `--doctor` produces a per-line install diagnostic
7. ⬜ **Manual smoke test by a human** — confirmed by a human user that the above six items behave on at least one OS

(7) is the gate that actually closes W5. PRs #83-#86 plus this ADR cover (1)-(6) on paper; (7) is the user smoke-test step.

---

## Open questions

- **None for now.** The decision is "defer", and the W5d author will face the open questions when packaging restarts. Listing them prematurely is design-by-anxiety.
