# Coordinate-system transforms — placeholder

**Lands:** Week 4 (RFC-001 §6.4) — only after at least two adapters
have surfaced their respective LCS conventions, so the API is
informed by real data instead of speculation.

**Inputs from adapter:** `FieldMetadata.coordinate_system` ∈
`{"global", "local", "nodal_local"}` plus an LCS handle (rotation
matrix or Euler angles, exact shape TBD).

**Output:** the same field's tensor / vector in the global frame.

**Trap reminder (§4.6 #1):** silently assuming "global" is the #1
ANSYS bug source for cross-solver consistency. The adapter MUST set
the frame; this layer MUST refuse to convert when it is `"unknown"`.
