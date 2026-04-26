"""Pure helpers for the visualization route — no fastapi / sqlalchemy.

R2 hardening (post Codex R1, 2026-04-26): these helpers were extracted
from `visualization.py` so they can be exercised by the dev test
environment, which doesn't ship fastapi/sqlalchemy. Validation errors
raise `ValueError`; the route translates to `HTTPException(400)`.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

# Strict case_id format. R2 hardening (post Codex R1 LOW path-traversal):
# anchor user-supplied identifiers to a known shape so a poisoned DB row
# can't be coerced into reading arbitrary filesystem paths via the
# candidate-probe in _resolve_frd_path.
_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _validate_case_id(case_id: str) -> None:
    """Reject case_ids that don't match the safe shape.

    Raises ValueError on bad input; route layer translates to HTTP 400.
    """
    if not _CASE_ID_RE.match(case_id or ""):
        raise ValueError("case_id has invalid shape")


def _allowed_fs_roots() -> list[Path]:
    """Allowed roots for FRD candidate resolution. Cwd-relative."""
    cwd = Path.cwd().resolve()
    return [
        (cwd / "golden_samples").resolve(),
        (cwd / "project_state").resolve(),
        (cwd / "calculix_cases").resolve(),
    ]


def _is_under_allowed_root(p: Path, roots: list[Path]) -> bool:
    """True if `p` resolves to a file under one of the allowed roots."""
    try:
        rp = p.resolve()
    except (OSError, RuntimeError):
        return False
    for root in roots:
        try:
            rp.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _resolve_frd_path(case_id: str, db_frd_path: str | None) -> Path | None:
    """Find the FRD result file for a case_id, honoring the on-disk
    naming variants (gs001_result.frd / gs-001.frd) AND the path-traversal
    guard. Returns None if no candidate resolves to a file under an
    allowed root.
    """
    cid_lower = case_id.lower().replace("-", "")
    case_dir = Path(db_frd_path).parent if db_frd_path else Path(f"./golden_samples/{case_id}")
    raw_candidates: list[Path | None] = [
        case_dir / f"{cid_lower}_result.frd",
        case_dir / f"{cid_lower}.frd",
        case_dir / f"{case_id.lower()}.frd",
        Path(db_frd_path).with_suffix(".frd") if db_frd_path else None,
        Path(db_frd_path) if db_frd_path else None,
    ]
    roots = _allowed_fs_roots()
    for candidate in raw_candidates:
        if not candidate:
            continue
        if not candidate.is_file():
            continue
        if not _is_under_allowed_root(candidate, roots):
            continue
        return candidate.resolve()
    return None


def _apply_increment(parsed: object, increment_index: int) -> None:
    """R2 (post Codex R1 MEDIUM): the FRD parser puts the LAST increment
    on the top-level `.displacements` / `.stresses`. The viz exporter
    reads only those top-level fields. To honor a non-default
    increment_index, we copy the chosen increment's data to the top
    level before rendering. No-op when the parser has no increments
    or the index is out of range.
    """
    increments = getattr(parsed, "increments", None) or []
    if not increments:
        return
    if not (0 <= increment_index < len(increments)):
        return
    inc = increments[increment_index]
    for attr in ("displacements", "stresses"):
        if hasattr(inc, attr) and hasattr(parsed, attr):
            setattr(parsed, attr, getattr(inc, attr))


def _fallback_html_unavailable_pyvista(case_name: str | None) -> str:
    """Server-side log diagnostic detail; client-side show only the case
    name + a generic message. R2 (post Codex R1 MEDIUM XSS): every
    interpolated value goes through html.escape; no internal paths or
    error strings leak to the browser."""
    safe_name = html.escape(case_name or "(unnamed case)")
    return (
        "<html><body style='background:#0d1117;color:#fff;padding:2rem;"
        "font-family:sans-serif'>"
        f"<h2>{safe_name}</h2>"
        "<p style='color:#f88'>3D scene unavailable: PyVista not installed.</p>"
        "</body></html>"
    )


def _fallback_html_render_failed(
    case_name: str | None,
    structure_type: str | None,
    n_nodes: int | str,
    n_elements: int | str,
    n_increments: int,
) -> str:
    """R2 (post Codex R1 MEDIUM XSS): all dynamic strings are escaped;
    server-internal paths and exception messages are NEVER returned to
    the client (logged server-side instead)."""
    safe_name = html.escape(case_name or "(unnamed case)")
    safe_struct = html.escape(structure_type or "")
    return f"""<html><body style='background:#0d1117;color:#fff;padding:2rem;font-family:system-ui,sans-serif;line-height:1.6'>
<h2 style='color:#39d353'>{safe_name}</h2>
<table style='border-collapse:collapse'>
<tr><td style='padding:4px 12px;color:#7d8590'>structure</td><td>{safe_struct}</td></tr>
<tr><td style='padding:4px 12px;color:#7d8590'>nodes</td><td>{n_nodes}</td></tr>
<tr><td style='padding:4px 12px;color:#7d8590'>elements</td><td>{n_elements}</td></tr>
<tr><td style='padding:4px 12px;color:#7d8590'>increments</td><td>{n_increments}</td></tr>
</table>
<p style='color:#f88;margin-top:2rem'>3D scene unavailable; rendering failed for all candidate fields.</p>
<p style='color:#7d8590;font-size:0.875rem'>FRD parsed successfully; check server logs for details.</p>
</body></html>"""
