"""AI-FEA quality checkers.

Pre-solve and post-mesh validation routines that gate the pipeline:
  - ``jacobian``: mesh quality (element Jacobian, aspect ratio).
  - ``geometry_checker``: watertightness, manifold validity.
"""
