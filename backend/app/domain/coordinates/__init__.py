"""Coordinate-system transforms — placeholder.

RFC-001 §4.6 trap #1: ANSYS / some Nastran sets emit fields in a local
coordinate frame; this module rotates everything into the global frame
before stress-derivative computation. The adapter only marks the
frame on ``FieldMetadata.coordinate_system``; the rotation lives here.
"""
