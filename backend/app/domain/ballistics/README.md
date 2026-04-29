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

Pre-gate candidate helpers:
  * `mean_velocity(velocities, *, node_indices=None) -> NDArray[float64]`
  * `residual_velocity_magnitude(velocities, *, projectile_node_indices) -> float`
  * `kinetic_energy(masses, velocities, *, node_indices=None) -> float`
  * `kinetic_energy_history(masses, velocities_by_step, *, node_indices=None) -> dict[int, float]`
  * `perforation_verdict_from_exit_plane(...) -> PerforationVerdict`

**ADR-001 reminder:** every derivation lives HERE. Adapters MUST NOT
compute eroded fractions, perforation flags, or displacement
trajectories. The OpenRadioss adapter's narrow ADR-001 carve-out
(DISPLACEMENT as `coorA(t)-coorA(0)`) is a coordinate-frame
re-expression, NOT a ballistic derivation.

**Still out of scope before ENG-22 approval:**
  * crater geometry (needs facet-connectivity analysis)
  * signed full-perforation verdict (needs approved benchmark + through-thickness evidence)
  * any claim that `GS-101-demo-unsigned` is a signed golden sample

**Test fixture:** v1 is exercised against GS-100 (degenerate
all-alive contact-only baseline) plus synthetic numpy arrays. GS-101
(W7e) will exercise the live-erosion path only after the governance
carve-out is approved.
