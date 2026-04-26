"""ANSYS (.rst) adapter — placeholder.

RFC-001 §4.5 work item: wrap ``ansys-mapdl-reader`` (PyAnsys, MIT) as
a Layer-1 ``ReaderHandle``. Lands in W6 per RFC §6.4. Beware §4.6
trap #1: ANSYS local coordinate systems must be flagged on
``FieldMetadata.coordinate_system`` and converted to global by
Layer-3, not by this adapter.
"""
