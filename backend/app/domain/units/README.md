# Unit conversion — placeholder

**Lands:** Week 3 (RFC-001 §6.4).

**Why this lives in Layer 3 not Layer 1:** ADR-003 forbids adapters
from "heuristically" deciding the unit system. The adapter only
copies what the file says; this module converts when the user has
explicitly pinned `UnitSystem` in the wizard.

**Conversion table seed:**

| from \ to | SI    | SI_mm   | English |
|-----------|-------|---------|---------|
| SI        | id    | scale   | scale   |
| SI_mm     | scale | id      | scale   |
| English   | scale | scale   | id      |

`UNKNOWN` is *not* a row — converting from / to UNKNOWN is a
programmer error and should raise.
