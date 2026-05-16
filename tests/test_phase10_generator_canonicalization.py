"""FM-04a Phase 10 E — generator script canonicalization SHA tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins:
* TRUST_SCORE_PROVENANCE_SCHEMA_VERSION == "1.2.0" (MINOR bump).
* GENERATOR_NORMALIZATION_METHOD pin (string SSOT).
* `_canonical_python_sha` is a pure function:
    - whitespace-equivalent scripts -> same normalized SHA, different raw SHA.
    - comment-equivalent scripts -> same normalized SHA, different raw SHA.
    - docstring-only differences -> same normalized SHA, different raw SHA.
    - any logic change -> different normalized SHA (and different raw SHA).
    - parse failure -> (None, "<ExcType>: <msg>") + method falls to None.
* Walker behavior:
    - generator-row carries sha256_normalized + method + None error on success.
    - generator-row falls back to None + error string on parse failure.
    - non-generator rows always have None for all three new fields.
    - generator-missing row has present=False + all four SHA/normalization
      fields None.
* JSON envelope contains all three new fields on every row.
* Forbidden-claim envelope audit still fires after the new fields land.

Phase 10 anti-gaming guard A: -3 — parse-failure path is exercised
by an explicit test (`test_canonical_python_sha_parse_failure_returns_none_plus_reason`).
Phase 10 anti-gaming guard T: -4 — whitespace AND comment AND
docstring equivalence each have their own test, not one combined.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from app.services.reporting._schema_versions import (
    TRUST_SCORE_PROVENANCE_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)
from app.services.reporting.trust_score_provenance import (
    GENERATOR_NORMALIZATION_METHOD,
    PROVENANCE_INPUT_KINDS,
    _canonical_python_sha,
    build_trust_score_provenance,
    render_trust_score_provenance_json,
)

# ---------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------


def test_schema_version_is_1_2_0() -> None:
    """Phase 10 E MINOR bump."""
    assert TRUST_SCORE_PROVENANCE_SCHEMA_VERSION == "1.2.0"


def test_normalization_method_name_pin() -> None:
    """Future algorithm changes must bump this string + a matching test
    (Phase 10 anti-gaming guard M: -2)."""
    assert GENERATOR_NORMALIZATION_METHOD == "python-ast-dump-v1"


# ---------------------------------------------------------------------
# `_canonical_python_sha` pure-function semantics
# ---------------------------------------------------------------------


def test_canonical_python_sha_returns_hex_digest_and_none_error() -> None:
    digest, err = _canonical_python_sha(b"x = 1\n")
    assert err is None
    assert digest is not None
    # sha256 hex digest is 64 lowercase hex chars.
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_canonical_python_sha_whitespace_equivalence() -> None:
    """Two scripts that differ only in trailing whitespace + blank
    lines + indentation style yield the SAME normalized SHA even though
    their raw SHAs differ."""
    a = b"def f():\n    return 1\n"
    b = b"def f():\n\n        return 1\n\n\n"  # different whitespace, same AST
    sha_a, err_a = _canonical_python_sha(a)
    sha_b, err_b = _canonical_python_sha(b)
    assert err_a is None and err_b is None
    assert sha_a == sha_b
    # And the *raw* SHA must differ — otherwise the test is vacuous.
    assert hashlib.sha256(a).hexdigest() != hashlib.sha256(b).hexdigest()


def test_canonical_python_sha_comment_equivalence() -> None:
    """Two scripts that differ only in comments yield the SAME
    normalized SHA. Comments are not AST nodes, so `ast.parse` drops
    them on the floor."""
    a = b"x = 1\n"
    b = b"# this is a comment\nx = 1  # trailing\n"
    sha_a, _ = _canonical_python_sha(a)
    sha_b, _ = _canonical_python_sha(b)
    assert sha_a == sha_b
    assert hashlib.sha256(a).hexdigest() != hashlib.sha256(b).hexdigest()


def test_canonical_python_sha_docstring_change_differs() -> None:
    """Two scripts that differ ONLY in a top-level module docstring
    yield DIFFERENT normalized SHAs. Docstrings ARE AST nodes
    (``Expr(Constant(...))``), so they belong to the canonical form —
    a reviewer who reworded a generator's docstring did make a
    real change to the captured AST. This is by design: if the
    project later wants comment+docstring equivalence it must bump
    the normalization method name + version + this test."""
    a = b'"""original docstring"""\nx = 1\n'
    b = b'"""rewritten docstring"""\nx = 1\n'
    sha_a, _ = _canonical_python_sha(a)
    sha_b, _ = _canonical_python_sha(b)
    assert sha_a != sha_b


def test_canonical_python_sha_logic_change_differs() -> None:
    """Any change to actual AST content (identifier rename, literal,
    operator, statement reorder) yields a different normalized SHA."""
    a = b"x = 1\n"
    b = b"x = 2\n"
    sha_a, _ = _canonical_python_sha(a)
    sha_b, _ = _canonical_python_sha(b)
    assert sha_a != sha_b
    # Reorder of independent assignments — order matters in AST.
    c = b"x = 1\ny = 2\n"
    d = b"y = 2\nx = 1\n"
    sha_c, _ = _canonical_python_sha(c)
    sha_d, _ = _canonical_python_sha(d)
    assert sha_c != sha_d


def test_canonical_python_sha_parse_failure_returns_none_plus_reason() -> None:
    """A generator whose bytes do not parse must yield
    ``(None, <reason>)`` instead of raising — the walker records the
    failure on the row rather than aborting the whole report."""
    digest, err = _canonical_python_sha(b"def broken(:\n    pass\n")
    assert digest is None
    assert err is not None
    assert "SyntaxError" in err


def test_canonical_python_sha_empty_input_parses_to_empty_module() -> None:
    """Empty bytes are a valid Python module (an empty AST). The
    canonical SHA exists and matches between two empty inputs."""
    sha_a, err_a = _canonical_python_sha(b"")
    sha_b, err_b = _canonical_python_sha(b"")
    assert err_a is None and err_b is None
    assert sha_a == sha_b


# ---------------------------------------------------------------------
# Walker — generator row carries canonical fields, non-generator rows do not
# ---------------------------------------------------------------------


def _seed_case(
    root: Path,
    case_id: str,
    *,
    with_generator: bool = True,
    generator_body: bytes = b"x = 1\n",
) -> SnapshotCaseInput:
    case_dir = root / "golden_samples" / case_id / "data"
    case_dir.mkdir(parents=True, exist_ok=True)
    starter = case_dir / "model_00_0000.rad"
    engine = case_dir / "model_00_0001.rad"
    starter.write_text("# s", encoding="utf-8")
    engine.write_text("# e", encoding="utf-8")
    metrics = (
        root / "project_state" / "graph_executor" / case_id / "ballistic" / "ballistic_metrics.json"
    )
    metrics.parent.mkdir(parents=True, exist_ok=True)
    metrics.write_text(json.dumps({"case_id": case_id, "claim_boundary": "tier1"}))
    generator: Path | None
    if with_generator:
        generator = root / "scripts" / f"gen_{case_id.lower().replace('-', '_')}.py"
        generator.parent.mkdir(parents=True, exist_ok=True)
        generator.write_bytes(generator_body)
    else:
        generator = None
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
        convergence_study_path=None,
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=generator,
        notes_path=None,
    )


def test_walker_emits_canonical_sha_for_generator_row(tmp_path: Path) -> None:
    body = b'"""hi"""\nx = 1\n'
    case = _seed_case(tmp_path, "GS-A-candidate", generator_body=body)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    gen_rows = [i for i in report.inputs if i.kind == "generator"]
    assert len(gen_rows) == 1
    row = gen_rows[0]
    assert row.present is True
    assert row.sha256 == hashlib.sha256(body).hexdigest()
    assert row.sha256_normalized is not None
    assert row.sha256_normalized != row.sha256  # canonical form differs from raw
    assert row.normalization_method == GENERATOR_NORMALIZATION_METHOD
    assert row.normalization_error is None


def test_walker_records_parse_failure_for_broken_generator(tmp_path: Path) -> None:
    body = b"def broken(:\n    pass\n"  # SyntaxError
    case = _seed_case(tmp_path, "GS-A-candidate", generator_body=body)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    row = next(i for i in report.inputs if i.kind == "generator")
    assert row.present is True
    assert row.sha256 == hashlib.sha256(body).hexdigest()
    # Canonical SHA is None on parse failure; method also None; error has reason.
    assert row.sha256_normalized is None
    assert row.normalization_method is None
    assert row.normalization_error is not None
    assert "SyntaxError" in row.normalization_error


def test_non_generator_rows_have_canonical_fields_none(tmp_path: Path) -> None:
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=False)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    # Every non-generator row must have None for all three new fields,
    # regardless of present/absent.
    for row in report.inputs:
        if row.kind == "generator":
            continue
        assert row.sha256_normalized is None, row.kind
        assert row.normalization_method is None, row.kind
        assert row.normalization_error is None, row.kind


def test_generator_missing_row_has_all_sha_fields_none(tmp_path: Path) -> None:
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=False)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    row = next(i for i in report.inputs if i.kind == "generator")
    assert row.present is False
    assert row.sha256 is None
    assert row.sha256_normalized is None
    assert row.normalization_method is None
    assert row.normalization_error is None


def test_walker_canonical_sha_matches_helper_output(tmp_path: Path) -> None:
    """The walker must produce the SAME sha256_normalized as a direct
    call to `_canonical_python_sha` on the same bytes — no second
    transformation hidden in the walker."""
    body = b"# comment\nx = 1 + 2\n"
    case = _seed_case(tmp_path, "GS-A-candidate", generator_body=body)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    row = next(i for i in report.inputs if i.kind == "generator")
    expected_sha, expected_err = _canonical_python_sha(body)
    assert row.sha256_normalized == expected_sha
    assert row.normalization_error == expected_err


def test_walker_whitespace_equivalence_yields_same_normalized_sha(
    tmp_path: Path,
) -> None:
    """Two cases with whitespace-only differences in their generator
    scripts produce DIFFERENT raw sha256 but SAME sha256_normalized
    — the load-bearing equivalence property of slice 10-E."""
    body_a = b"x = 1\n"
    body_b = b"x = 1\n\n\n"  # different whitespace, same AST
    case_a = _seed_case(tmp_path, "GS-A-candidate", generator_body=body_a)
    case_b = _seed_case(tmp_path, "GS-B-candidate", generator_body=body_b)
    write_cohort_snapshot([case_a, case_b], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report_a = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    report_b = build_trust_score_provenance(
        "GS-B-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    row_a = next(i for i in report_a.inputs if i.kind == "generator")
    row_b = next(i for i in report_b.inputs if i.kind == "generator")
    assert row_a.sha256 != row_b.sha256  # raw differs
    assert row_a.sha256_normalized == row_b.sha256_normalized  # canonical matches


def test_walker_logic_change_yields_different_normalized_sha(tmp_path: Path) -> None:
    """A real logic change in the generator script changes both raw
    and normalized SHAs — the canonicalization is not over-eager."""
    case_a = _seed_case(tmp_path, "GS-A-candidate", generator_body=b"x = 1\n")
    case_b = _seed_case(tmp_path, "GS-B-candidate", generator_body=b"x = 2\n")
    write_cohort_snapshot([case_a, case_b], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report_a = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    report_b = build_trust_score_provenance(
        "GS-B-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    row_a = next(i for i in report_a.inputs if i.kind == "generator")
    row_b = next(i for i in report_b.inputs if i.kind == "generator")
    assert row_a.sha256 != row_b.sha256
    assert row_a.sha256_normalized != row_b.sha256_normalized


# ---------------------------------------------------------------------
# JSON envelope
# ---------------------------------------------------------------------


def test_json_envelope_includes_canonical_fields_on_every_row(tmp_path: Path) -> None:
    case = _seed_case(tmp_path, "GS-A-candidate", generator_body=b"x = 1\n")
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    payload = json.loads(render_trust_score_provenance_json(report))
    assert payload["schema_version"] == "1.2.0"
    assert len(payload["inputs"]) == len(PROVENANCE_INPUT_KINDS)
    for row in payload["inputs"]:
        # Every row must carry all three new keys, even when None.
        assert "sha256_normalized" in row
        assert "normalization_method" in row
        assert "normalization_error" in row
    # The generator row alone has populated canonical fields.
    gen = next(r for r in payload["inputs"] if r["kind"] == "generator")
    assert gen["sha256_normalized"] is not None
    assert gen["normalization_method"] == "python-ast-dump-v1"
    assert gen["normalization_error"] is None


def test_forbidden_claim_audit_still_fires_after_canonical_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The envelope audit must continue to catch a forbidden positive
    claim in the rendered JSON — adding three new fields must NOT
    silently bypass the audit (Phase 10 anti-gaming guard C: -4)."""
    case = _seed_case(tmp_path, "GS-A-candidate", generator_body=b"x = 1\n")
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    # Patch CLAIM_IMPACT_DEFAULT to insert a forbidden claim WITHOUT the
    # "not " prefix. Build should then refuse.
    import app.services.reporting.trust_score_provenance as mod

    monkeypatch.setattr(
        mod,
        "CLAIM_IMPACT_DEFAULT",
        "this trace is validated physics for the cohort",
    )
    with pytest.raises(ValueError, match="forbidden positive claim"):
        build_trust_score_provenance("GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path)
