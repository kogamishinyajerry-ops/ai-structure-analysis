"""Render the FM-03 candidate report spine (v2) as a Tier 1 Markdown report.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

This module is a pure function over the spine dict produced by
``candidate_report_spine.build_candidate_report_spine``. It performs no
network I/O, reads no files, and never alters spine fields. It exists to
let a reviewer eyeball the same evidence the JSON spine carries without
parsing JSON by hand.

Wording discipline (ADR-023):
- Output must NOT contain any phrase from FORBIDDEN_PHRASES *as an
  affirmative claim* — i.e. without a preceding negation marker
  ("not ", "no public ", "explicitly not ", etc.). The Tier 1 spine
  itself is full of legitimate negation forms ("not benchmark
  agreement"), so a naive substring check would forbid its own
  required boundary text.
- Output MUST contain the spine's claim_tier and no_overclaim tokens
  verbatim.
- ``render_candidate_report`` raises ValueError if either guard fails
  (defensive against future schema drift introducing overclaim
  language).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

# ADR-023 §Forbidden Claims + ADR-024 (lite) extensions. Listed lower-case;
# matched only when NOT preceded by a negation marker (see
# _NEGATION_MARKERS) within the lookbehind window.
FORBIDDEN_PHRASES: tuple[str, ...] = (
    "validated physics",
    "benchmark agreement",
    "signed gs evidence",
    "signed gs101",
    "signed gs102",
    "signed validation",
    "steel perforation completed",
    "bullet-through-steel complete",
    "bullet-through-steel simulation complete",
    "validated against børvik",
    "validated against borvik",
)

# Markers that, when present anywhere on the same line as a forbidden
# phrase, render that occurrence a legitimate Tier 1 non-affirmative
# usage (negation, precondition, deferral, etc.) rather than an
# overclaim. Lower-case; matched on the lowered line.
_NON_AFFIRMATIVE_MARKERS: tuple[str, ...] = (
    # Negation
    "not ",
    "not_",
    "no public ",
    "no signed ",
    "no benchmark ",
    "without ",
    "never ",
    "explicitly not ",
    "explicitly_not_",
    # Precondition / deferral / aspiration
    "before ",
    "prior to ",
    "until ",
    "pending ",
    "awaiting ",
    "deferred",
    "defer ",
    "requires ",
    "requiring ",
    "blocked",
    "blocker",
    "missing",
    "remain blocked",
    "remains blocked",
    # Spine-internal vocabulary that surfaces forbidden phrases as evidence labels
    "tier2_blockers",
    "tier 2 blocker",
    "claim_boundary",
    "claim_impact",
    "forbidden",
    "no_overclaim",
    "next_actions",
    "next action",
)

# Claim-boundary phrases the renderer is REQUIRED to surface verbatim. These
# come from the spine itself (claim_tier / no_overclaim / tier2_blockers) and
# the renderer must not paraphrase them.
_REQUIRED_BOUNDARY_TOKENS: tuple[str, ...] = (
    "Tier 1 engineering candidate",
    "not signed validation",
)


def render_candidate_report(spine: Mapping[str, Any]) -> str:
    """Render a spine v2 dict as Markdown. Pure function.

    Raises
    ------
    ValueError
        If the spine schema_version does not start with
        ``fm03-candidate-report-spine.``, or if the rendered text contains
        any FORBIDDEN_PHRASES (defense-in-depth against schema drift).
    """
    schema_version = str(spine.get("schema_version", ""))
    if not schema_version.startswith("fm03-candidate-report-spine."):
        raise ValueError(
            f"unsupported spine schema_version: {schema_version!r}; "
            "expected fm03-candidate-report-spine.*"
        )

    sections: list[str] = []
    sections.append(_render_header(spine))
    sections.append(_render_case(spine.get("case", {})))
    sections.append(_render_provenance(spine.get("provenance", {})))
    sections.append(_render_solver(spine.get("solver", {})))
    sections.append(_render_assumptions(spine.get("assumptions", {})))
    sections.append(_render_mesh_evidence(spine.get("mesh_evidence", {})))
    sections.append(_render_convergence_evidence(spine.get("convergence_evidence", {})))
    sections.append(_render_ballistic(spine.get("ballistic", {})))
    sections.append(_render_metrics(spine.get("metrics", {}), spine.get("validation", {})))
    sections.append(_render_artifact_manifest(spine.get("artifact_manifest", {})))
    sections.append(_render_limitations(spine.get("limitations", [])))
    sections.append(_render_reviewer_summary(spine.get("reviewer_summary", {})))
    sections.append(_render_tier2_blockers(spine.get("tier2_blockers", [])))

    text = "\n\n".join(section for section in sections if section)
    _enforce_wording_discipline(text)
    return text + "\n"


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_header(spine: Mapping[str, Any]) -> str:
    case = spine.get("case", {})
    case_id = case.get("case_id", "uploaded-artifact")
    case_name = case.get("case_name", case_id)
    claim_tier = spine.get("claim_tier", "Tier 1 engineering candidate")
    no_overclaim = spine.get("no_overclaim", "not signed validation")
    allowed_claim = spine.get("allowed_claim", "engineering candidate, not signed validation")
    generated_at = spine.get("generated_at_utc", "unknown")
    schema_version = spine.get("schema_version", "fm03-candidate-report-spine.v2")

    lines = [
        f"# Candidate Report — {case_name}",
        "",
        f"> **Claim tier:** {claim_tier}  ",
        f"> **Boundary:** {no_overclaim}; not benchmark agreement; not signed validation  ",
        f"> **Allowed claim:** {allowed_claim}",
        "",
        f"- **case_id**: `{case_id}`",
        f"- **schema_version**: `{schema_version}`",
        f"- **generated_at_utc**: {generated_at}",
    ]
    return "\n".join(lines)


def _render_case(case: Mapping[str, Any]) -> str:
    if not case:
        return ""
    rows = [
        ("case_id", case.get("case_id", "—")),
        ("case_name", case.get("case_name", "—")),
        ("expected_results_status", case.get("expected_results_status", "—")),
        ("status_reason", case.get("status_reason", "—")),
        ("failure_pattern_ref", case.get("failure_pattern_ref", "—")),
    ]
    return "## Case\n\n" + _kv_table(rows)


def _render_provenance(provenance: Mapping[str, Any]) -> str:
    if not provenance:
        return ""
    rows = [
        ("report_surface", provenance.get("report_surface", "—")),
        ("parser", provenance.get("parser", "—")),
        ("result_file_name", provenance.get("result_file_name", "—")),
        ("original_filename", provenance.get("original_filename", "—")),
        ("file_size_bytes", provenance.get("file_size_bytes", "—")),
        ("parse_time_s", provenance.get("parse_time_s", "—")),
        ("is_binary_frd", provenance.get("is_binary_frd", "—")),
        ("node_count", provenance.get("node_count", "—")),
        ("element_count", provenance.get("element_count", "—")),
        ("increment_count", provenance.get("increment_count", "—")),
        ("solver_truth_source", provenance.get("solver_truth_source", "—")),
    ]
    return "## Provenance\n\n" + _kv_table(rows)


def _render_solver(solver: Mapping[str, Any]) -> str:
    if not solver:
        return ""
    rows = [
        ("truth_source", solver.get("truth_source", "—")),
        ("latest_job_id", solver.get("latest_job_id", "—")),
        ("latest_job_status", solver.get("latest_job_status", "—")),
        ("normal_termination_state", solver.get("normal_termination_state", "—")),
    ]
    out = ["## Solver", "", _kv_table(rows)]

    logs = solver.get("logs", {})
    if logs:
        out.append("")
        out.append("**Logs**")
        out.append("")
        log_rows = [
            ("status", logs.get("status", "—")),
            ("line_count", logs.get("line_count", 0)),
            ("artifact_paths", _join_or_dash(logs.get("artifact_paths", []))),
        ]
        if logs.get("unavailable_reason"):
            log_rows.append(("unavailable_reason", logs["unavailable_reason"]))
        out.append(_kv_table(log_rows))
        tail = logs.get("tail") or []
        if tail:
            out.append("")
            out.append("```")
            out.extend(str(line) for line in tail)
            out.append("```")
    return "\n".join(out)


def _render_assumptions(assumptions: Mapping[str, Any]) -> str:
    if not assumptions:
        return ""
    out = ["## Assumptions", ""]

    unit_system = assumptions.get("unit_system", {})
    if unit_system:
        out.append("**Unit system**")
        out.append("")
        out.append(_kv_table([(k, v) for k, v in unit_system.items()]))
        out.append("")

    for key in ("material", "boundary_conditions", "contact"):
        block = assumptions.get(key, {})
        if not block:
            continue
        out.append(f"**{key.replace('_', ' ').capitalize()}**")
        out.append("")
        out.append(_kv_table([(k, _scalarize(v)) for k, v in block.items()]))
        out.append("")

    return "\n".join(out).rstrip()


def _render_mesh_evidence(mesh: Mapping[str, Any]) -> str:
    if not mesh:
        return ""
    out = ["## Mesh evidence", ""]
    out.append(f"- **status**: `{mesh.get('status', '—')}`")
    if mesh.get("claim_impact"):
        out.append(f"- **claim_impact**: {mesh['claim_impact']}")
    out.append("")

    result_mesh = mesh.get("result_mesh", {})
    if result_mesh:
        out.append("**Result mesh (from FRD)**")
        out.append("")
        out.append(
            _kv_table(
                [
                    ("source", result_mesh.get("source", "—")),
                    ("node_count", result_mesh.get("node_count", "—")),
                    ("element_count", result_mesh.get("element_count", "—")),
                    ("increment_count", result_mesh.get("increment_count", "—")),
                ]
            )
        )
        out.append("")

    deck = mesh.get("input_deck", {})
    if deck:
        out.append("**Input deck**")
        out.append("")
        deck_rows = [
            ("status", deck.get("status", "—")),
            ("path", deck.get("path", "—")),
        ]
        for key in (
            "node_count",
            "element_count",
            "include_count",
            "limitation",
            "unavailable_reason",
        ):
            if key in deck:
                deck_rows.append((key, _scalarize(deck.get(key))))
        elem_types = deck.get("element_types") or {}
        if elem_types:
            deck_rows.append(("element_types", _scalarize(elem_types)))
        out.append(_kv_table(deck_rows))
        out.append("")

    quality = mesh.get("quality", {})
    if quality:
        out.append("**Quality**")
        out.append("")
        quality_rows = [("status", quality.get("status", "—"))]
        for key in ("source", "unavailable_reason", "claim_impact"):
            if quality.get(key):
                quality_rows.append((key, _scalarize(quality[key])))
        metrics = quality.get("metrics") or {}
        if metrics:
            quality_rows.append(("metrics", _scalarize(metrics)))
        out.append(_kv_table(quality_rows))
        out.append("")

    convergence = mesh.get("convergence_study", {})
    if convergence:
        out.append("**Mesh refinement convergence study**")
        out.append("")
        out.append(_render_convergence_study_block(convergence))

    return "\n".join(out).rstrip()


def _render_convergence_evidence(convergence: Mapping[str, Any]) -> str:
    if not convergence:
        return ""
    out = ["## Solver-side convergence evidence", ""]
    out.append(f"- **status**: `{convergence.get('status', '—')}`")
    if convergence.get("claim_impact"):
        out.append(f"- **claim_impact**: {convergence['claim_impact']}")
    out.append(f"- **normal_termination**: `{convergence.get('normal_termination', '—')}`")
    out.append(f"- **latest_job_status**: `{convergence.get('latest_job_status', '—')}`")
    signals = convergence.get("signals") or []
    if signals:
        out.append(f"- **signals**: {', '.join(f'`{s}`' for s in signals)}")
    out.append("")

    missing = convergence.get("missing_reasons") or []
    if missing:
        out.append("**Missing reasons**")
        out.append("")
        for reason in missing:
            out.append(f"- {reason}")
        out.append("")

    artifacts = convergence.get("source_artifacts") or []
    if artifacts:
        out.append(f"**Source artifacts** ({len(artifacts)})")
        out.append("")
        for art in artifacts:
            kind = art.get("kind", "?")
            path = art.get("path", "—")
            status = art.get("status", "?")
            out.append(f"- `{kind}` — {path} ({status})")
            for sig in art.get("signals", []) or []:
                out.append(f"    - signal: `{sig}`")
        out.append("")
    return "\n".join(out).rstrip()


def _render_ballistic(ballistic: Mapping[str, Any]) -> str:
    if not ballistic:
        return ""
    out = ["## Ballistic candidate evidence", ""]
    out.append(f"- **status**: `{ballistic.get('status', '—')}`")
    if ballistic.get("claim_impact"):
        out.append(f"- **claim_impact**: {ballistic['claim_impact']}")
    if ballistic.get("claim_boundary"):
        out.append(f"- **claim_boundary**: `{ballistic['claim_boundary']}`")
    out.append("")

    v0 = ballistic.get("projectile_initial_velocity", {})
    vR = ballistic.get("residual_velocity_candidate", {})
    perf = ballistic.get("perforation_marker", {})
    out.append("**Velocities and perforation marker**")
    out.append("")
    out.append(
        _kv_table(
            [
                ("V₀ (initial, m/s)", _scalarize(v0.get("value_m_per_s"))),
                ("V₀ status", v0.get("status", "—")),
                ("V₀ source", v0.get("source") or v0.get("unavailable_reason", "—")),
                ("vR (residual candidate, m/s)", _scalarize(vR.get("value_m_per_s"))),
                ("vR status", vR.get("status", "—")),
                ("perforation_marker", perf.get("status", "—")),
                (
                    "perforation_marker source",
                    perf.get("evidence_path") or perf.get("unavailable_reason", "—"),
                ),
            ]
        )
    )
    out.append("")

    energy = ballistic.get("energy_balance_candidate", {})
    if energy:
        out.append("**Energy balance (candidate health indicator)**")
        out.append("")
        energy_rows = [("status", energy.get("status", "—"))]
        for key in (
            "initial_kinetic_energy_j",
            "plastic_dissipation_j",
            "contact_friction_j",
            "hourglass_energy_j",
            "residual_kinetic_energy_j",
            "energy_ratio",
        ):
            energy_rows.append((key, _scalarize(energy.get(key))))
        if energy.get("unavailable_reason"):
            energy_rows.append(("unavailable_reason", energy["unavailable_reason"]))
        if energy.get("claim_impact"):
            energy_rows.append(("claim_impact", energy["claim_impact"]))
        out.append(_kv_table(energy_rows))
        out.append("")

    series = ballistic.get("time_step_series_summary", {})
    if series:
        out.append("**Time-step series summary**")
        out.append("")
        series_rows = [("status", series.get("status", "—"))]
        for key in (
            "source",
            "step_count",
            "min_dt_s",
            "max_dt_s",
            "mean_dt_s",
            "unavailable_reason",
        ):
            if key in series:
                series_rows.append((key, _scalarize(series.get(key))))
        out.append(_kv_table(series_rows))
        out.append("")

    convergence = ballistic.get("time_step_convergence_study", {})
    if convergence:
        out.append("**Time-step refinement convergence study**")
        out.append("")
        out.append(_render_convergence_study_block(convergence))
        out.append("")

    blockers = ballistic.get("tier2_blockers_ballistic") or []
    if blockers:
        out.append("**Ballistic Tier 2 blockers**")
        out.append("")
        for b in blockers:
            out.append(f"- {b}")
        out.append("")

    return "\n".join(out).rstrip()


def _render_metrics(metrics: Mapping[str, Any], validation: Mapping[str, Any]) -> str:
    if not metrics and not validation:
        return ""
    out = ["## Metrics", ""]
    if metrics:
        keys = metrics.get("output_metric_keys") or []
        keys_str = ", ".join(f"`{k}`" for k in keys) if keys else "—"
        out.append(f"- **output_metric_keys**: {keys_str}")
        if metrics.get("extraction_command"):
            out.append(f"- **extraction_command**: `{metrics['extraction_command']}`")
        out.append("")
        values = metrics.get("values") or {}
        if values:
            out.append("**Values**")
            out.append("")
            out.append(_kv_table([(str(k), _scalarize(v)) for k, v in values.items()]))
            out.append("")
    if validation:
        out.append("**Validation**")
        out.append("")
        out.append(_kv_table([(str(k), _scalarize(v)) for k, v in validation.items()]))
    return "\n".join(out).rstrip()


def _render_artifact_manifest(manifest: Mapping[str, Any]) -> str:
    if not manifest:
        return ""
    out = ["## Artifact manifest", ""]
    out.append(f"- **manifest_id**: `{manifest.get('manifest_id', '—')}`")
    out.append(f"- **hash_algorithm**: `{manifest.get('hash_algorithm', '—')}`")
    out.append(f"- **hash_count**: {manifest.get('hash_count', 0)}")
    items = manifest.get("items") or []
    out.append(f"- **item_count**: {len(items)}")
    out.append("")
    if items:
        out.append("| kind | status | path | size_bytes | sha256 (12) |")
        out.append("|---|---|---|---|---|")
        for it in items:
            sha = (it.get("sha256") or "")[:12]
            out.append(
                "| `{kind}` | `{status}` | {path} | {size} | `{sha}` |".format(
                    kind=it.get("kind", "?"),
                    status=it.get("status", "?"),
                    path=it.get("path", "—"),
                    size=it.get("size_bytes", "—"),
                    sha=sha or "—",
                )
            )
    return "\n".join(out)


def _render_limitations(limitations: Iterable[Any]) -> str:
    items = list(limitations)
    if not items:
        return ""
    out = ["## Limitations", ""]
    for limit in items:
        out.append(f"- {limit}")
    return "\n".join(out)


def _render_reviewer_summary(summary: Mapping[str, Any]) -> str:
    if not summary:
        return ""
    out = ["## Reviewer summary", ""]
    out.append(f"- **verdict**: `{summary.get('verdict', '—')}`")
    if summary.get("summary"):
        out.append(f"- **summary**: {summary['summary']}")
    out.append("")
    findings = summary.get("blocked_findings") or []
    if findings:
        out.append("**Blocked findings**")
        out.append("")
        for f in findings:
            out.append(f"- {f}")
        out.append("")
    actions = summary.get("next_actions") or []
    if actions:
        out.append("**Next actions**")
        out.append("")
        for a in actions:
            out.append(f"- {a}")
    return "\n".join(out).rstrip()


def _render_tier2_blockers(blockers: Iterable[Any]) -> str:
    items = list(blockers)
    if not items:
        return ""
    out = ["## Tier 2 blockers (always present at Tier 1)", ""]
    for b in items:
        out.append(f"- {b}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _render_convergence_study_block(study: Mapping[str, Any]) -> str:
    rows = [
        ("status", study.get("status", "—")),
        ("study_status", study.get("study_status", "—")),
        ("parameter", study.get("parameter", "—")),
        ("metric", study.get("metric", "—")),
        ("tolerance_pct", _scalarize(study.get("tolerance_pct"))),
        ("relative_change_pct", _scalarize(study.get("relative_change_pct"))),
        ("candidate_stability", study.get("candidate_stability", "—")),
        ("run_count", study.get("run_count", 0)),
        ("source", study.get("source", "—")),
    ]
    if study.get("unavailable_reason"):
        rows.append(("unavailable_reason", study["unavailable_reason"]))
    if study.get("claim_boundary"):
        rows.append(("claim_boundary", study["claim_boundary"]))
    if study.get("claim_impact"):
        rows.append(("claim_impact", study["claim_impact"]))
    out = [_kv_table(rows)]

    runs = study.get("runs") or []
    if runs:
        out.append("")
        out.append("| label | parameter_value | metric_value |")
        out.append("|---|---|---|")
        for run in runs:
            out.append(
                "| {label} | {pv} | {mv} |".format(
                    label=run.get("label", "—"),
                    pv=_scalarize(run.get("parameter_value")),
                    mv=_scalarize(run.get("metric_value")),
                )
            )
    return "\n".join(out)


def _kv_table(rows: list[tuple[str, Any]]) -> str:
    out = ["| field | value |", "|---|---|"]
    for key, value in rows:
        out.append(f"| `{key}` | {_scalarize(value)} |")
    return "\n".join(out)


def _scalarize(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value != value:  # NaN
            return "NaN"
        return f"{value:g}"
    if isinstance(value, (int,)):
        return str(value)
    if isinstance(value, str):
        return value if value else "—"
    if isinstance(value, Mapping):
        if not value:
            return "—"
        parts = [f"{k}={_scalarize(v)}" for k, v in value.items()]
        return ", ".join(parts)
    if isinstance(value, (list, tuple)):
        if not value:
            return "—"
        return ", ".join(_scalarize(item) for item in value)
    return str(value)


def _join_or_dash(items: Iterable[Any]) -> str:
    items = list(items)
    if not items:
        return "—"
    return ", ".join(f"`{item}`" for item in items)


def _enforce_wording_discipline(text: str) -> None:
    # Required-boundary check first so that bad spines that drop the
    # "Tier 1 engineering candidate" / "not signed validation" tokens
    # are reported as omission errors rather than masked by the
    # affirmative-overclaim check below.
    missing = [token for token in _REQUIRED_BOUNDARY_TOKENS if token not in text]
    if missing:
        raise ValueError(
            f"candidate-report renderer omitted required Tier 1 boundary tokens: {missing!r}"
        )

    affirmative_hits = _affirmative_forbidden_hits(text)
    if affirmative_hits:
        raise ValueError(
            "candidate-report renderer produced forbidden Tier-2 wording "
            f"(ADR-023 violation): {sorted(set(affirmative_hits))!r}"
        )


def _affirmative_forbidden_hits(text: str) -> list[str]:
    """Per-line scan: forbidden phrase + no non-affirmative marker on the
    same line ⇒ overclaim. The Tier 1 spine references forbidden phrases
    constantly as evidence labels (Tier 2 blockers, next actions, claim
    boundaries) — those lines always carry a marker like ``not`` /
    ``before`` / ``deferred`` / ``tier2_blockers`` that the marker set
    captures.
    """
    hits: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in line and not any(marker in line for marker in _NON_AFFIRMATIVE_MARKERS):
                hits.append(phrase)
    return hits


__all__ = ["render_candidate_report", "FORBIDDEN_PHRASES"]
