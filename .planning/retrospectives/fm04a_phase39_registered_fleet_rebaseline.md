# FM-04a Phase 39 Retro — registered-fleet prospective re-baseline + proxy-drift correction

> 2026-05-25. Composite re-baselined to **80.67** under the first authoritative
> REGISTERED eval-fleet pass. Phase 38 (78.33) + Phase 37 (77.50) unchanged.

## What happened
1. **Registry blocker diagnosed + durably fixed.** Prior sessions ran the eval
   fleet via `general-purpose` proxies because `subagent_type=functional-tester
   /novice-simulator/industrial-ui-comparator` weren't discovered. Root cause:
   the Agent registry loads only from `~/.claude/agents/` (user-level) + plugins,
   never `<repo>/.claude/agents/`, and only at session init. Last session's
   "launch from project dir" hypothesis was wrong. Fix: installed the 3 wrappers
   at `~/.claude/agents/` with ABSOLUTE protocol paths + a restart. The registry
   does NOT hot-reload (confirmed empirically before the restart).
2. **First authoritative registered-fleet composite in FM-04a.** Dim 2=82 /
   Dim 1=86 / Dim 5=82 / Dim 3=76 from the registered fleet; Dim 4=80 + Dim 6=78
   main synthesis. Composite 80.67.

## The load-bearing finding: proxy drift is BIDIRECTIONAL, and the registered fleet caught it
- **Dim 1: proxy 91 → registered 86 (−5, generous drift).** The Phase 38
  `general-purpose` proxy claimed the 90-anchor "fully met + 1/5 toward 95." It
  is NOT: Richardson coverage is 38.5% < the 60% the 90-anchor requires. The
  registered fleet, reading the same byte-unchanged FEA code, correctly lands 86.
  **Phase 38 banked a +5 generous read on Dim 1 that the registered fleet now
  reverses.**
- **Dim 5: proxy 84 → registered 82 (−2, correct-reason).** The proxy over-credited
  the 90-anchor "comparison cuts (overlay two results)" by misreading
  CompanionViewport. The registered fleet confirms CompanionViewport is
  side-by-side compare-CUTS of ONE result (`CompanionViewport.tsx:53-61`, single
  `frame` prop) — NOT an overlay of two. So 82 (80 fully + CSV only), not 84.
- **Dim 4/5 stale carries: +4 / +10.** Conversely, Phase 38 *conservatively held*
  Phase-37 values (76/72) on byte-unchanged code; the authoritative reads are 80/82.

**Lesson:** the proxy era was inconsistent — it *adopted* a generous proxy read on
Dim 1 (banked 91) but *held* conservative stale values on Dim 4/5 (72/76). The
registered fleet normalizes both: down where over-credited, up where under-credited.
This is exactly the "校准双向警惕" the re-score was charged to watch.

## Methodology patches
1. **Registered fleet is now the SSOT scorer.** No more proxy re-scores. The
   `~/.claude/agents/` install + ABSOLUTE protocol paths make it cwd-independent;
   any future session (from any dir) discovers the fleet after a normal launch.
   If a session ever reports the fleet missing again: check `~/.claude/agents/`
   exists (not just `<repo>/.claude/agents/`), then restart — do NOT fall back to
   proxies for an authoritative score.
2. **Don't bank proxy scores as authoritative.** Phase 38's Dim 1=91 is the
   cautionary case: a proxy "fresh real work" read was adopted into the composite
   and proved +5 generous. Proxy reads are directional signals only.
3. **Hold, don't inflate, the synthesis-only dims.** Dim 6 (no fleet agent) was
   held at its Phase 38 fresh value (78), not pushed up — the anti-inflation
   discipline that keeps the re-baseline credible.

## Recommended next (post-re-baseline)
- **Dim 5 → 90** is the highest-ROI single move: iso-surface rendering + a real
  playwright WebGL E2E suite (`frontend/e2e/`) + (optionally) a true two-result
  overlay. Three of the four 90-anchor sub-bullets are viz-buildable.
- **Dim 1 → 90** needs Richardson coverage 38.5% → ≥60% (≈8 of 13 cases) — add
  `convergence_study.json` to ~3 more refinable cases. The other 90-anchor
  sub-bullets are already met.
- **Dim 2 → 90** needs role-branching onboarding (4 personas) + WCAG AA audit +
  the 2 missing error-recovery paths (results-iframe, BC-mismatch).
- **Debt-cleanup phase** (separate, behavior-sensitive, NOT drive-by): `tsc -b`
  16 + eslint 69 + the 4 backend httpx collection errors + GS-001 legacy marker +
  the dev "Phase X" label leak.

24th consecutive Tier-2 phase. Local-commit only; nothing pushed.
