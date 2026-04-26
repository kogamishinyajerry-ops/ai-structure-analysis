# CalculiX adapter — placeholder

**Lands:** Week 2 (RFC-001 §6.4).

**Strategy:** rewrap Sprint-2 `parsers/frd_parser.py` as a
`ReaderHandle` per `app.core.types.ReaderHandle`. ADR-001/003/004
apply: no derived quantities here, no UNIT-system inference, no caches.

**Done criterion (W2 row of §6.4):** `GS-001` end-to-end pipes
σ_max within 5 % of the analytical solution (7.5 MPa).

**Reference fields per §4.4:**

| CanonicalField   | CalculiX field |
|------------------|----------------|
| DISPLACEMENT     | `DISP` (NODE)            |
| STRESS_TENSOR    | `STRESS` (NODE, 外推)     |
| STRAIN_TENSOR    | `TOSTRAIN`               |
| REACTION_FORCE   | `FORC`                   |
| ELEMENT_VOLUME   | 自算 (no native field)    |
