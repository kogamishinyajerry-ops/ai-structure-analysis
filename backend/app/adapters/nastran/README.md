# Nastran adapter — placeholder

**Lands:** Week 3 (RFC-001 §6.4).

**Strategy:** wrap [`pyNastran`](https://github.com/SteveDoyle2/pyNastran)
(BSD, 10y mature). 1-week effort per §4.5.

**Done criterion (W3 row of §6.4):** GS-002 (thick-walled cylinder
internal pressure) cross-solver consistency CalculiX↔Nastran passes
the §4.7 tolerances.

**Why ahead of ANSYS:** pyNastran is the most mature OSS reader on the
solver list. Wiring it second after CalculiX lets us flush the Layer-2
contract on a stable, well-trodden codebase before exposing the
contract to the messier ANSYS / Abaqus reads.
