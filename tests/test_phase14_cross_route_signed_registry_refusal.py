"""FM-04a Phase 14 A — cross-route signed-registry refusal meta-guard.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Closes Phase 13 retrospective slice-B LOW #3 carry-forward (cross-route
signed-registry meta-guard). Phase 11 introduced the signed-registry
refusal at advisor-critique; Phase 13 B closed the equivalent gap on
case-completeness; Phase 14 A consolidates the discipline across every
Tier 1 reviewer-facing ``/api/v1/.*/{case_id}`` route.

The meta-guard enumerates every ``/{case_id}`` route via FastAPI
route introspection and asserts each one consistently:

  1. Returns ``422`` (NOT 400 / 404 / 200) on ``^GS-\\d{3}$`` input.
  2. The 422 detail contains the canonical vocabulary
     ``"signed-registry"`` + ``"candidate"`` + ``"out of scope"``.

A new ``/{case_id}`` route that omits the gate trips the meta-test
with the unfamiliar route path in the failure message. The
``_KNOWN_CASE_ID_ROUTES`` SSOT tuple + ``_OPT_OUT_ROUTES`` opt-out
list together pin the expected enumeration so the meta-test is also
a SCHEMA CHECK on the route set: any route addition / removal /
rename must be reflected in the SSOT.

Anti-gaming guards exercised:

* **M:-2** — ``_KNOWN_CASE_ID_ROUTES`` + ``_OPT_OUT_ROUTES`` are
  module-level typed tuples; importing them anywhere uses the SSOT.
* **T:-3** — per-route parametrize so a per-route failure surfaces
  with the route path in the test name.
* **T:-4** — schema-check test asserts the introspected route set
  equals ``_KNOWN_CASE_ID_ROUTES ∪ _OPT_OUT_ROUTES``; silent route
  additions trip this test.
* **C:-8** — the canonical detail vocabulary contains no forbidden
  positive-claim tokens.
* **A:-7** — defense-in-depth pin: the 422 fires BEFORE any
  filesystem lookup so a tampered registry directory cannot leak
  through the route.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from app.api.routes._signed_registry_refusal import (
    SIGNED_REGISTRY_RE,
    assert_not_signed_registry,
    signed_registry_refusal_detail,
)
from app.main import app
from fastapi import HTTPException


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str, params: dict | None = None) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(transport=self._transport, base_url="http://t") as c:
                return await c.get(url, params=params)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


# ---------------------------------------------------------------------
# SSOT enumeration of `/{case_id}` routes
# ---------------------------------------------------------------------

# Routes that MUST refuse signed-registry case_ids with 422 + canonical
# detail. Each tuple = (method, path-template, query-string-extras).
# Query-string-extras is needed for routes that require additional
# query params (e.g., advisor-critique needs `?snapshot=<label>`,
# trust-score-provenance needs `?snapshot=<label>`) so the probe can
# reach the 422 gate INSTEAD of tripping a 422 on missing-required-query.
_KNOWN_CASE_ID_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("GET", "/api/v1/acceptance-packet/{case_id}", ""),
    ("GET", "/api/v1/advisor-critique/{case_id}", "?snapshot=2026-05-16T120000Z"),
    ("GET", "/api/v1/case-completeness/{case_id}", ""),
    ("GET", "/api/v1/convergence-study/{case_id}", ""),
    ("GET", "/api/v1/report/export/pdf/{case_id}", ""),
    ("GET", "/api/v1/reproducibility-manifest/{case_id}", ""),
    ("GET", "/api/v1/signoff-history/{case_id}", ""),
    ("GET", "/api/v1/tier1-report/{case_id}", ""),
    ("GET", "/api/v1/trust-score-alerts/{case_id}", ""),
    (
        "GET",
        "/api/v1/trust-score-provenance/{case_id}",
        "?snapshot=2026-05-16T120000Z",
    ),
    ("GET", "/api/v1/trust-score-timeline/{case_id}", ""),
    ("GET", "/api/v1/trust-score/{case_id}", ""),
    ("GET", "/api/v1/visualize/result-mesh/{case_id}", ""),
)

# Routes that are explicitly NOT Tier 1 reviewer-facing and therefore
# do NOT participate in the signed-registry refusal contract. Each
# entry MUST carry an inline rationale in the comment.
_OPT_OUT_ROUTES: tuple[tuple[str, str], ...] = (
    # Generic case-fetching workbench API backed by the application
    # database; not the `golden_samples/` reviewer evidence surface.
    # The route returns the database row regardless of the case_id
    # shape and is not part of the Tier 1 disclaimer trio surface.
    ("GET", "/api/v1/cases/{case_id}"),
    # NL copilot chat history. Pre-Phase-1.5 frozen surface with a
    # double-prefix bug (`/api/v1/api/v1/history/{case_id}`). Not a
    # Tier 1 reviewer-facing route; opt-out documented for the
    # meta-test enumeration check.
    ("GET", "/api/v1/api/v1/history/{case_id}"),
    # POST + GET on result-mesh artifact sub-path. The PARENT route
    # `/api/v1/visualize/result-mesh/{case_id}` is in
    # `_KNOWN_CASE_ID_ROUTES`; the artifact sub-route inherits the
    # parent's gate via the same handler module + helper call.
    # Listed here so the schema-check test's enumeration matches.
    (
        "GET",
        "/api/v1/visualize/result-mesh/{case_id}/{artifact_path:path}",
    ),
    # POST signoff-history is in scope (and uses the helper since
    # Phase 14 A), but the schema-check enumeration tracks GET-only
    # routes; the POST behavior is pinned by
    # tests/test_phase9_signoff_post_endpoint.py separately.
    ("POST", "/api/v1/signoff-history/{case_id}"),
)


def _introspect_case_id_routes() -> set[tuple[str, str]]:
    """Return the set of ``(method, path)`` tuples for every route
    whose path template contains ``{case_id}``."""
    routes: set[tuple[str, str]] = set()
    for r in app.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None) or set()
        if not path or "{case_id}" not in path:
            continue
        for m in methods:
            if m in ("HEAD", "OPTIONS"):
                continue
            routes.add((m, path))
    return routes


# ---------------------------------------------------------------------
# 1. SSOT schema-check (T:-4)
# ---------------------------------------------------------------------


def test_known_routes_match_app_introspection() -> None:
    """The introspected ``/{case_id}`` route set MUST equal
    ``_KNOWN_CASE_ID_ROUTES ∪ _OPT_OUT_ROUTES``. A silent route
    addition / removal / rename trips this test.

    Adding a new ``/{case_id}`` route requires updating one of the
    two SSOT tuples:
      * Add to ``_KNOWN_CASE_ID_ROUTES`` if it is a Tier 1
        reviewer-facing surface (and call the SSOT helper from the
        route handler).
      * Add to ``_OPT_OUT_ROUTES`` if it is genuinely NOT a Tier 1
        surface (with inline rationale).
    """
    introspected = _introspect_case_id_routes()
    declared = {(m, p) for (m, p, _q) in _KNOWN_CASE_ID_ROUTES}
    opt_outs = set(_OPT_OUT_ROUTES)
    expected = declared | opt_outs
    extra = introspected - expected
    missing = expected - introspected
    assert not extra, (
        f"App has {len(extra)} `/{{case_id}}` routes not declared in "
        f"_KNOWN_CASE_ID_ROUTES or _OPT_OUT_ROUTES: {sorted(extra)}"
    )
    assert not missing, (
        f"SSOT declares {len(missing)} routes that are no longer in the app: {sorted(missing)}"
    )


# ---------------------------------------------------------------------
# 2. Per-route 422 contract (T:-3)
# ---------------------------------------------------------------------


@pytest.mark.parametrize("method,path_template,query_extras", _KNOWN_CASE_ID_ROUTES)
def test_route_refuses_signed_registry_with_canonical_422(
    client: _SyncASGIClient,
    method: str,
    path_template: str,
    query_extras: str,
) -> None:
    """Every Tier 1 reviewer-facing ``/{case_id}`` route refuses
    ``GS-001`` with 422 + canonical detail vocabulary."""
    url = path_template.replace("{case_id}", "GS-001") + query_extras
    if method == "GET":
        res = client.get(url)
    else:
        raise NotImplementedError(f"method {method!r} not supported by sync client")
    assert res.status_code == 422, (
        f"{method} {url}: expected 422, got {res.status_code}; body: {res.text[:200]}"
    )
    payload = res.json()
    detail = payload.get("detail") if isinstance(payload, dict) else None
    assert isinstance(detail, str), (
        f"{method} {url}: expected str detail, got {type(detail).__name__}"
    )
    assert "signed-registry" in detail, (
        f"{method} {url}: detail missing 'signed-registry' token: {detail!r}"
    )
    assert "candidate" in detail, f"{method} {url}: detail missing 'candidate' token: {detail!r}"
    assert "out of scope" in detail, (
        f"{method} {url}: detail missing 'out of scope' token: {detail!r}"
    )


# ---------------------------------------------------------------------
# 3. Per-route variant: every ^GS-\d{3}$ shape trips the gate
# ---------------------------------------------------------------------


@pytest.mark.parametrize("case_id", ["GS-000", "GS-101", "GS-102", "GS-999"])
def test_signed_registry_shape_variants_all_refused_on_anchor_route(
    client: _SyncASGIClient, case_id: str
) -> None:
    """The canonical case-completeness route refuses every ``^GS-\\d{3}$``
    shape, not just ``GS-001``. Pins the closed-set discipline against
    a future regex narrowing that accidentally lets one shape through."""
    res = client.get(f"/api/v1/case-completeness/{case_id}")
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert "signed-registry" in detail


# ---------------------------------------------------------------------
# 4. Non-signed-registry candidate names pass the gate
# ---------------------------------------------------------------------


def test_candidate_case_id_passes_the_gate(client: _SyncASGIClient) -> None:
    """A ``*-candidate`` case_id is NOT refused by the gate; the
    route's normal handler logic runs. (The case may still legitimately
    404 if no fixture exists, but the 422 gate must NOT fire.)
    """
    res = client.get("/api/v1/case-completeness/some-imaginary-candidate")
    # 422 is the gate's status; anything else means the gate passed.
    assert res.status_code != 422 or "signed-registry" not in res.json().get("detail", "")


# ---------------------------------------------------------------------
# 5. SSOT helper unit pins (M:-2 / A:-7)
# ---------------------------------------------------------------------


def test_signed_registry_re_is_fullmatch_anchored() -> None:
    """The SSOT regex is fullmatch-anchored ``^GS-\\d{3}$``. A
    relaxation (e.g., to ``match``) would let `GS-101-candidate`
    pass the helper, regressing the Phase 13 E MEDIUM-1 closure
    discipline."""
    assert SIGNED_REGISTRY_RE.pattern == r"^GS-\d{3}$"
    assert SIGNED_REGISTRY_RE.fullmatch("GS-001") is not None
    assert SIGNED_REGISTRY_RE.fullmatch("GS-101-candidate") is None
    assert SIGNED_REGISTRY_RE.fullmatch("gs-001") is None
    assert SIGNED_REGISTRY_RE.fullmatch("GS-1000") is None


def test_assert_helper_passes_on_candidate_id() -> None:
    """The helper does NOT raise on ``*-candidate`` ids."""
    assert_not_signed_registry("cylinder-pv-candidate", "test-surface")
    assert_not_signed_registry("modal-cantilever-candidate", "test-surface")
    assert_not_signed_registry("GS-101-candidate", "test-surface")  # not ^GS-\d{3}$


def test_assert_helper_raises_422_on_signed_registry() -> None:
    """The helper raises ``HTTPException(422)`` with the canonical
    detail message when given a signed-registry id."""
    with pytest.raises(HTTPException) as exc_info:
        assert_not_signed_registry("GS-001", "trust-score")
    assert exc_info.value.status_code == 422
    detail = exc_info.value.detail
    assert "trust-score" in detail
    assert "signed-registry" in detail
    assert "out of scope" in detail


def test_signed_registry_refusal_detail_embeds_surface_name() -> None:
    """The detail-formatter embeds the surface name verbatim so a
    reviewer reading the 422 response sees WHICH surface refused."""
    detail = signed_registry_refusal_detail("my-custom-surface")
    assert "my-custom-surface" in detail
    assert "signed-registry" in detail
    assert "candidate" in detail
    assert "out of scope" in detail


# ---------------------------------------------------------------------
# 6. Opt-out routes are documented + still function
# ---------------------------------------------------------------------


def test_opt_out_routes_are_documented_in_methodology() -> None:
    """Every opt-out route MUST appear in the methodology doc with a
    rationale. This pin trips if the opt-out list grows without a
    methodology-doc update."""
    from pathlib import Path

    doc = (
        Path(__file__).resolve().parent.parent
        / ".planning"
        / "methodology"
        / "case_id_route_discipline.md"
    )
    text = doc.read_text(encoding="utf-8")
    for _method, path in _OPT_OUT_ROUTES:
        # Use the path STEM (without the {case_id} part) so the doc
        # mention doesn't need to embed the FastAPI template syntax.
        stem = path.split("{")[0].rstrip("/")
        # `/api/v1/cases/` -> `/api/v1/cases` for the doc grep.
        assert stem in text or path in text, (
            f"opt-out route {path!r} (stem {stem!r}) is missing a "
            f"documented rationale in {doc.name}"
        )


def test_opt_out_count_is_pinned() -> None:
    """The opt-out list size is pinned so a silent growth (without
    methodology-doc + retro update) trips the test."""
    assert len(_OPT_OUT_ROUTES) == 4, (
        "_OPT_OUT_ROUTES grew/shrank; update the count pin + the "
        "methodology doc + the retrospective"
    )


def test_canonical_detail_vocabulary_contains_no_forbidden_tokens() -> None:
    """The cross-route canonical refusal message uses no forbidden
    positive-claim tokens. C:-8 pin."""
    detail = signed_registry_refusal_detail("test-surface")
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
        "production ready",
        "certified",
        "approved for service",
        "asme compliant",
        "signed off",
    )
    detail_lower = detail.lower()
    for token in forbidden:
        assert token not in detail_lower, (
            f"canonical refusal detail contains forbidden token {token!r}: {detail!r}"
        )
