"""Unit conversion — placeholder.

RFC-001 §4.6 trap #6 + ADR-003: unit handling is the #1 silent
killer; conversion code lives here and consults the user-pinned
``UnitSystem`` rather than guessing. ``Quantity.to`` (in
``app.core.types.quantity``) is implemented from this module in W3.
"""
