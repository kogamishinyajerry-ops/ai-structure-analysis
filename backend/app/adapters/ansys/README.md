# ANSYS adapter — placeholder

**Lands:** Week 6 (RFC-001 §6.4).

**Strategy:** wrap [`ansys-mapdl-reader`](https://github.com/pyansys/pymapdl-reader)
(PyAnsys, MIT). 1-week effort per §4.5.

**Done criterion (W6 row of §6.4):** GS-003 (lifting lug) cross-solver
consistency vs CalculiX/Nastran:
  * `max disp` deviation ≤ 0.5 %
  * `max stress` deviation ≤ 1 %

**Trap #1 reminder (§4.6):** `result_cs` in ANSYS may be a *local*
coordinate frame. The adapter MUST mark
`FieldMetadata.coordinate_system = "local"` and emit the LCS rotation
matrix as auxiliary metadata; coordinate-system normalisation lives in
`app.domain.coordinates`.
