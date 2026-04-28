# Ballistic derivations — RFC-001 §6.4 W7d

**Lands:** Week 7 (RFC-001 §6.4 W7d).

**API surface (v1):**

Tier 1 — pure-array helpers (no reader dep):
  * `count_alive(flags: NDArray[int8]) -> int`
  * `count_eroded(flags: NDArray[int8]) -> int`
  * `eroded_fraction(flags: NDArray[int8]) -> float`
  * `max_displacement_magnitude(disp: NDArray[float64]) -> float`

Tier 2 — reader-aware orchestrators:
  * `eroded_history(reader: SupportsElementDeletion, step_ids) -> dict[int, int]`
  * `perforation_event_step(reader: SupportsElementDeletion, step_ids) -> int | None`
  * `displacement_history(reader: ReaderHandle, step_ids, *, node_indices=None) -> dict[int, float]`

**ADR-001 reminder:** every derivation lives HERE. Adapters MUST NOT
compute eroded fractions, perforation flags, or displacement
trajectories. The OpenRadioss adapter's narrow ADR-001 carve-out
(DISPLACEMENT as `coorA(t)-coorA(0)`) is a coordinate-frame
re-expression, NOT a ballistic derivation.

**Out of scope for v1 (deferred to W7d-v2 once GS-101 lands):**
  * residual velocity (needs projectile-node tagging)
  * crater geometry (needs facet-connectivity analysis)
  * full-perforation verdict (needs through-thickness erosion path)

**Test fixture:** v1 is exercised against GS-100 (degenerate
all-alive contact-only baseline) plus synthetic numpy arrays. GS-101
(W7e) will exercise the live-erosion path.
