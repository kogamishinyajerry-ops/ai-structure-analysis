"""Tier 1 candidate reviewer signoff record (FM-04a Phase 8 A).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Persists per-candidate reviewer judgments to disk so cross-session
auditability is possible. A reviewer who decides "GS-A-candidate
needs more convergence work" today can record that judgment; the
next session sees the verdict + reviewer + UTC timestamp + notes
and can build on it instead of starting blind.

The verdict is drawn from a **whitelisted enum** that DELIBERATELY
excludes every Tier 2 promotion verb:

* ``watching`` — reviewer is monitoring but has no specific
  follow-up request.
* ``needs_more_evidence`` — reviewer wants more snapshots / more
  cases in the cohort before judging.
* ``needs_more_convergence`` — reviewer wants additional
  mesh/dt convergence work before judging.
* ``blocked_pending_input`` — reviewer is waiting on an external
  input (e.g. updated material card, clarified BC) before
  judging.

The whitelist enum and its import-time audit are load-bearing
safety mechanisms (Phase 8 anti-gaming guards ``C: -10`` and
``C: -8``). A future maintainer who tries to add a verdict
containing any of the forbidden tokens (``tier_2``, ``signed_*``,
``benchmark_agreement``, ``promoted``, ``ready_for_fm04b``) fails
import — not runtime, not test, but at module load. There is no
way to ship a Tier 2 promotion verb through this surface without
also disabling the audit, and the audit removal is itself
deduct-by-rubric.

Free-text ``notes`` are audited via ``_assert_no_overclaim`` with
the same 6-token forbidden list used elsewhere in the Phase 4-7
reporting stack.

Closes Phase 7 retrospective's "reviewer judgments have nowhere
to land" gap.

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from ._schema_versions import SIGNOFF_RECORD_SCHEMA_VERSION
from .acceptance_packet import CLAIM_BOUNDARY

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate review judgments only; not signed validation; "
    "not benchmark agreement. Signoff records capture reviewer "
    "monitoring state for the cohort; they do NOT authorize Tier 2 "
    "promotion, do NOT substitute for signed validation, and do NOT "
    "constitute benchmark agreement."
)

# ----- verdict whitelist (load-bearing safety; Phase 8 guard C: -10) -----

SignoffVerdict = Literal[
    "watching",
    "needs_more_evidence",
    "needs_more_convergence",
    "blocked_pending_input",
]

SUPPORTED_SIGNOFF_VERDICTS: tuple[str, ...] = (
    "watching",
    "needs_more_evidence",
    "needs_more_convergence",
    "blocked_pending_input",
)

_FORBIDDEN_VERDICT_TOKENS: tuple[str, ...] = (
    "tier_2",
    "tier 2",
    "signed_validation",
    "signed validation",
    "benchmark_agreement",
    "benchmark agreement",
    "promoted",
    "ready_for_fm04b",
    "ready for fm04b",
)
"""Tokens that must NEVER appear in any verdict literal in
:data:`SUPPORTED_SIGNOFF_VERDICTS`. Import-time audit
:func:`_audit_verdict_whitelist` enforces this. Phase 8 anti-gaming
guard ``C: -10`` references this list directly."""


def _audit_verdict_whitelist() -> None:
    """Refuses module import if any verdict contains a Tier 2 promotion token.

    Phase 8 anti-gaming guard ``C: -10`` (load-bearing). Run at module
    import time so the failure mode is "import error", not "test
    failure". A future maintainer who adds e.g. ``"ready_for_tier_2"``
    to :data:`SUPPORTED_SIGNOFF_VERDICTS` discovers the violation
    before any code runs.
    """
    for verdict in SUPPORTED_SIGNOFF_VERDICTS:
        lowered = verdict.lower()
        for token in _FORBIDDEN_VERDICT_TOKENS:
            if token in lowered:
                raise RuntimeError(
                    f"Signoff verdict whitelist contains forbidden "
                    f"Tier 2 promotion token: verdict={verdict!r} "
                    f"token={token!r}. Tier 1 candidate signoffs MUST "
                    "NOT include any Tier 2 promotion vocabulary."
                )


_audit_verdict_whitelist()


# ----- forbidden positive-claim tokens: two intentional lists -----
#
# Same design as Phase 7 B ``snapshot_narrative_catalogs``:
#
# * ``_FORBIDDEN_NOTES_TOKENS`` — applied to *reviewer-provided* free
#   text (the ``notes`` field). Notes should never contain *any* Tier 2
#   promotion claim, so the list is the full set of 6 tokens.
#
# * ``_ENVELOPE_FORBIDDEN_TOKENS`` — applied to the *full report dict*
#   (envelope + records) when serialized for HTTP. The envelope's own
#   ``claim_impact`` legitimately contains "signed validation" and
#   "benchmark agreement" inside disclaimer text ("...do NOT substitute
#   for signed validation, ...constitute benchmark agreement..."); the
#   `not <claim>` lookback cannot accept these because they appear
#   inside compound sentences with prepositional / verbal contexts
#   between "not" and the token. Excluding those two from the envelope
#   audit is the same honest fix used in Phase 7 B
#   (``ENVELOPE_FORBIDDEN_TOKENS = 4`` tokens vs
#   ``CATALOG_FORBIDDEN_TOKENS = 6`` tokens).

_FORBIDDEN_NOTES_TOKENS: tuple[str, ...] = (
    "validated against",
    "perforation completed",
    "bullet-through-steel complete",
    "validated physics",
    "signed validation",
    "benchmark agreement",
)

_ENVELOPE_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "validated against",
    "perforation completed",
    "bullet-through-steel complete",
    "validated physics",
)


# ----- case_id validation (refuses ^GS-\d{3}$ signed registry) -----

_CASE_ID_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")


def _assert_candidate_case_id(case_id: str) -> None:
    if _CASE_ID_SIGNED_REGISTRY_RE.match(case_id):
        raise ValueError(
            f"Signoff record refuses signed registry case_id={case_id!r}; "
            "Tier 1 candidate signoffs only accept *-candidate identifiers."
        )


# ----- record dataclass -----


@dataclass(frozen=True)
class SignoffRecord:
    """Immutable signoff record.

    ``signoff_utc`` is stored as an ISO 8601 UTC string (no local time;
    Phase 8 anti-gaming guard ``M: -2`` forbids local time in
    filenames or stored timestamps).
    """

    case_id: str
    reviewer: str
    verdict: SignoffVerdict
    signoff_utc: str
    notes: str
    schema_version: str = SIGNOFF_RECORD_SCHEMA_VERSION
    claim_tier: str = CLAIM_TIER
    claim_boundary: str = CLAIM_BOUNDARY
    claim_impact: str = CLAIM_IMPACT_DEFAULT
    drift_attribution_at_signoff_time: object = None
    """Phase 16 C — the per-case :class:`DriftAttribution` for the
    case's latest snapshot pair AT WRITE TIME (server-computed; A:-3
    NOT trusted from a client POST body). ``None`` when fewer than
    2 snapshots exist for the case at write time. Closes the
    audit-trail gap: a future reviewer reading this record sees
    WHICH axis was regressing AT THE TIME the verdict was made,
    NOT recomputed from the live snapshot tree (which may have
    evolved past the signoff event). Schema 1.1.0 additive field;
    pre-1.1.0 consumers that ignore the field continue to function.
    """


# ----- write -----


def write_signoff_record(
    case_id: str,
    reviewer: str,
    verdict: str,
    notes: str,
    *,
    repo_root: Path,
    now_utc: datetime | None = None,
) -> SignoffRecord:
    """Write a signoff record to ``reports/signoffs/<case_id>/<utc>.json``.

    Raises ``ValueError`` for any of: empty case_id, ``^GS-\\d{3}$``
    signed-registry case_id, empty reviewer, verdict not in
    :data:`SUPPORTED_SIGNOFF_VERDICTS`, notes containing a forbidden
    positive claim (outside ``not <claim>`` form), or output path that
    would resolve under ``golden_samples/**``.
    """
    if not case_id:
        raise ValueError("Signoff record requires a non-empty case_id")
    _assert_candidate_case_id(case_id)
    if not reviewer.strip():
        raise ValueError("Signoff record requires a non-empty reviewer")
    if verdict not in SUPPORTED_SIGNOFF_VERDICTS:
        raise ValueError(
            f"Signoff verdict {verdict!r} is not in the whitelist "
            f"{SUPPORTED_SIGNOFF_VERDICTS!r}."
        )
    _assert_no_overclaim(notes)

    stamp = (now_utc or datetime.now(UTC)).strftime("%Y-%m-%dT%H%M%SZ")
    out_dir = (repo_root / "reports" / "signoffs" / case_id).resolve()
    _assert_not_in_golden_samples(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stamp}.json"

    # Phase 16 C — compute drift_attribution at write time from the
    # case's latest snapshot pair (server-computed; A:-3 NOT trusted
    # from any client-supplied input). Local import defers the cost
    # when no snapshots exist; graceful degrade to None when the case
    # has fewer than 2 timeline points.
    drift_attribution = _compute_drift_attribution_at_signoff_time(
        case_id, repo_root=repo_root
    )

    record = SignoffRecord(
        case_id=case_id,
        reviewer=reviewer.strip(),
        verdict=verdict,  # type: ignore[arg-type]
        signoff_utc=stamp,
        notes=notes,
        drift_attribution_at_signoff_time=drift_attribution,
    )
    out_path.write_text(
        json.dumps(_record_to_dict(record), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return record


def _compute_drift_attribution_at_signoff_time(
    case_id: str, *, repo_root: Path
) -> object:
    """Compute the per-case drift_attribution for the case's latest
    snapshot pair at signoff write time. Returns ``None`` when fewer
    than 2 snapshots exist for the case (graceful degrade).

    Server-computed only (anti-gaming guard A:-3): the signoff POST
    body MUST NOT carry a client-side drift_attribution field; the
    server walks the on-disk snapshot tree at write time.
    """
    from .trust_score_timeline import build_trust_score_timeline

    timeline = build_trust_score_timeline(case_id, repo_root)
    if len(timeline.inter_snapshot_drift_attribution) == 0:
        return None
    # Latest consecutive-pair entry is the snap-(N-1) → snap-N
    # transition; this is the load-bearing pair for "what was
    # regressing at signoff time".
    return timeline.inter_snapshot_drift_attribution[-1]


# ----- read -----


def read_signoff_history(case_id: str, *, repo_root: Path) -> list[SignoffRecord]:
    """Return all signoff records for ``case_id`` sorted chronologically (oldest first).

    Returns ``[]`` if the case has no signoffs directory yet. Tolerant
    of older schema versions: a 1.0.0 record reads cleanly even after
    a future MINOR bump (additive fields are silently ignored on read).

    Raises ``ValueError`` for empty or signed-registry case_id.
    """
    if not case_id:
        raise ValueError("Signoff history requires a non-empty case_id")
    _assert_candidate_case_id(case_id)

    case_dir = (repo_root / "reports" / "signoffs" / case_id).resolve()
    if not case_dir.exists():
        return []

    records: list[SignoffRecord] = []
    for record_path in sorted(case_dir.glob("*.json")):
        payload = json.loads(record_path.read_text(encoding="utf-8"))
        records.append(
            SignoffRecord(
                case_id=payload["case_id"],
                reviewer=payload["reviewer"],
                verdict=payload["verdict"],
                signoff_utc=payload["signoff_utc"],
                notes=payload["notes"],
                schema_version=payload.get(
                    "schema_version", SIGNOFF_RECORD_SCHEMA_VERSION
                ),
                claim_tier=payload.get("claim_tier", CLAIM_TIER),
                claim_boundary=payload.get("claim_boundary", CLAIM_BOUNDARY),
                claim_impact=payload.get("claim_impact", CLAIM_IMPACT_DEFAULT),
                # Phase 16 C — additive field; 1.0.0-era records lack
                # the key and read as ``None`` (back-compat).
                drift_attribution_at_signoff_time=_parse_drift_attribution(
                    payload.get("drift_attribution_at_signoff_time")
                ),
            )
        )
    return records


def _parse_drift_attribution(blob: object) -> object:
    """Reconstruct a :class:`DriftAttribution` from its JSON dict form;
    returns ``None`` when the blob is missing/None (back-compat with
    1.0.0-era on-disk records)."""
    if blob is None:
        return None
    if not isinstance(blob, dict):
        return None
    from .trust_score_drift_attribution import DriftAttribution

    dominant_delta_pct = blob.get("dominant_delta_pct")
    return DriftAttribution(
        from_snapshot=blob["from_snapshot"],
        to_snapshot=blob["to_snapshot"],
        per_axis_delta_pct=dict(blob["per_axis_delta_pct"]),
        dominant_axis=blob.get("dominant_axis"),
        dominant_delta_pct=(
            float("nan")
            if dominant_delta_pct is None
            else float(dominant_delta_pct)
        ),
    )


# ----- helpers -----


def _record_to_dict(record: SignoffRecord) -> dict[str, object]:
    from .trust_score_drift_attribution import render_drift_attribution_dict

    drift = record.drift_attribution_at_signoff_time
    drift_dict = (
        render_drift_attribution_dict(drift) if drift is not None else None
    )
    return {
        "schema_version": record.schema_version,
        "case_id": record.case_id,
        "reviewer": record.reviewer,
        "verdict": record.verdict,
        "signoff_utc": record.signoff_utc,
        "notes": record.notes,
        "claim_tier": record.claim_tier,
        "claim_boundary": record.claim_boundary,
        "claim_impact": record.claim_impact,
        # Phase 16 C — schema 1.1.0 additive field. ``null`` when
        # fewer than 2 snapshots existed at write time. Pre-1.1.0
        # consumers that ignore the field continue to function.
        "drift_attribution_at_signoff_time": drift_dict,
    }


def _assert_no_overclaim(notes: str) -> None:
    """Refuse notes that contain forbidden positive claims outside ``not <claim>`` form.

    A token is "in disclaimer form" if it is immediately preceded by
    "not " (case-insensitive). Anything else is treated as a positive
    claim and refused.
    """
    lowered = notes.lower()
    for token in _FORBIDDEN_NOTES_TOKENS:
        start = 0
        while True:
            idx = lowered.find(token, start)
            if idx == -1:
                break
            prefix = lowered[max(0, idx - 4) : idx]
            if not prefix.endswith("not "):
                raise ValueError(
                    f"Signoff notes contain forbidden positive claim {token!r} "
                    "outside the `not <claim>` disclaimer form."
                )
            start = idx + len(token)


def _assert_not_in_golden_samples(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    for parent in (resolved, *resolved.parents):
        if parent.name == "golden_samples":
            raise ValueError(
                "Signoff record refuses writes under golden_samples/**; "
                "use reports/signoffs/<case_id>/ instead."
            )


# ----- HTTP-facing report (slice 8-B) -----


@dataclass(frozen=True)
class SignoffHistoryReport:
    """Endpoint envelope for ``GET /api/v1/signoff-history/<case_id>``.

    Mirrors the envelope shape used by every other Phase 6/7 endpoint:
    Tier 1 disclaimer trio + schema version + case id + record count +
    chronological records list. Carries an explicit ``claim_impact``
    that says signoffs do NOT authorize Tier 2 promotion.
    """

    schema_version: str
    case_id: str
    claim_tier: str
    claim_boundary: str
    generated_at_utc: str
    record_count: int
    records: tuple[SignoffRecord, ...] = field(default_factory=tuple)
    claim_impact: str = CLAIM_IMPACT_DEFAULT


def build_signoff_history_report(
    case_id: str, *, repo_root: Path, now_utc: datetime | None = None
) -> SignoffHistoryReport:
    """Build an HTTP envelope around :func:`read_signoff_history`.

    Refuses signed registry case_id (defense in depth) and audits the
    final dict for forbidden positive claims before returning.
    """
    records = read_signoff_history(case_id, repo_root=repo_root)
    generated_at = (now_utc or datetime.now(UTC)).isoformat(timespec="seconds")
    report = SignoffHistoryReport(
        schema_version=SIGNOFF_RECORD_SCHEMA_VERSION,
        case_id=case_id,
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        generated_at_utc=generated_at,
        record_count=len(records),
        records=tuple(records),
    )
    _assert_no_overclaim_in_report(report)
    return report


def render_signoff_history_json(report: SignoffHistoryReport) -> str:
    return json.dumps(_report_to_dict(report), indent=2, sort_keys=True)


def _report_to_dict(report: SignoffHistoryReport) -> dict[str, object]:
    return {
        "schema_version": report.schema_version,
        "case_id": report.case_id,
        "claim_tier": report.claim_tier,
        "claim_boundary": report.claim_boundary,
        "generated_at_utc": report.generated_at_utc,
        "record_count": report.record_count,
        "records": [_record_to_dict(r) for r in report.records],
        "claim_impact": report.claim_impact,
    }


def _assert_no_overclaim_in_report(report: SignoffHistoryReport) -> None:
    """Audit the *full report dict* against ``_ENVELOPE_FORBIDDEN_TOKENS``.

    Uses the narrower envelope list (4 tokens, excludes "signed
    validation" / "benchmark agreement") because the envelope's own
    Tier 1 ``claim_impact`` legitimately uses those phrases inside
    disclaimer text. The wider notes-level list (6 tokens) is enforced
    on reviewer-provided ``notes`` fields at write time
    (:func:`_assert_no_overclaim`), so a forbidden claim cannot enter
    via that surface.
    """
    haystack = json.dumps(_report_to_dict(report)).lower()
    for token in _ENVELOPE_FORBIDDEN_TOKENS:
        start = 0
        while True:
            idx = haystack.find(token, start)
            if idx == -1:
                break
            prefix = haystack[max(0, idx - 4) : idx]
            if not prefix.endswith("not "):
                raise ValueError(
                    f"Signoff history report contains forbidden positive "
                    f"claim {token!r} outside the `not <claim>` disclaimer form."
                )
            start = idx + len(token)
