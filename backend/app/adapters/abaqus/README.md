# Abaqus adapter — placeholder (stub-quality for MVP)

**Lands:** Week 6 — *stub only*. Full coverage M7+ (RFC-001 §6.5
done-gate #4 + §8 phase M7-M12).

**Strategy:** subprocess + helper script (`odb_export.py`) the user
runs in an Abaqus-equipped Python interpreter to convert ODB → HDF5;
this adapter reads the HDF5 (open format, h5py).

**Why a stub for MVP:** Abaqus licensing forbids redistributing
ODB-reading code; commercial libraries (FEAcrunch etc.) need
per-seat licences that conflict with the wedge price point. The
free path is "ask the user to run the helper themselves".

**Done criterion (W6, gate #4):** `odb_export.py` exists, is
documented, and the adapter can read its output for a known
GS-001-equivalent input.
