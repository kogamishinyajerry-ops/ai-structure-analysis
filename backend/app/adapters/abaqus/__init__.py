"""Abaqus (.odb-derived .h5) adapter — placeholder.

RFC-001 §4.5: Abaqus has no open-source ODB reader, so the strategy is
to ship a helper script (``odb_export.py``) the user runs *inside* an
Abaqus environment to convert ODB → HDF5; this adapter then reads the
HDF5. M3 ships a stub-quality helper + this adapter; full coverage
slips to M7+ per §6.5 done-gate #4.
"""
