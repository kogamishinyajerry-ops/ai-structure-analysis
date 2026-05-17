"""Materials library — FM-04a Phase 18 C.

A small, citable structured material database backing the Tier 2
mesh+materials pipeline. The Phase 18 C cohort intentionally starts
small (3 materials covering 3 industrial classes) — Phase 18+ grows
the library as solver coverage broadens.

Every material entry MUST carry a citation source (per ADR-025 §3 anti-
gaming guard C:-1). A material without a ``reference`` field fails the
SSOT loader, which prevents the library from silently accumulating
made-up property values.
"""

from .api import (
    DEFAULT_LIBRARY_PATH,
    Material,
    MaterialNotFoundError,
    MaterialLibraryError,
    get_material,
    list_materials,
    load_library,
)

__all__ = [
    "DEFAULT_LIBRARY_PATH",
    "Material",
    "MaterialNotFoundError",
    "MaterialLibraryError",
    "get_material",
    "list_materials",
    "load_library",
]
