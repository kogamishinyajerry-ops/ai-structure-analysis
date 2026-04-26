# Stress derivatives — placeholder

**Lands:** Week 3 (RFC-001 §6.4).

**API surface (planned):**
  * `von_mises(stress_tensor: NDArray) -> NDArray`
  * `principals(stress_tensor: NDArray) -> tuple[NDArray, NDArray, NDArray]`
  * `max_shear(stress_tensor: NDArray) -> NDArray`
  * `linearize_along_path(...)` — ASME VIII Div 2 SCL, lands M4+

**ADR-001 reminder:** these functions take canonical-form tensors
(`STRESS_TENSOR` per `CanonicalField`) and return scalars. Adapters
MUST NOT call them; adapters expose the raw tensor and Layer-3
chooses when to derive.
