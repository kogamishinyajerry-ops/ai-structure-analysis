"""FM-04a Phase 9 B — generator input kind in provenance + snapshot.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins:
* PROVENANCE_INPUT_KINDS length 5 with ``generator`` last + tuple order.
* Cohort snapshot manifest schema 1.3.0; provenance schema 1.1.0.
* Generator-present case yields present=True + SHA over captured bytes.
* Generator-missing case yields present=False + sha256=None.
* Forward-compat read: a 1.0.0-era snapshot (no generator/ subdir)
  reads back cleanly through the 1.1.0 walker.
* Snapshot writer's `generator/` subdirectory is created idempotently
  and only landed via `members` when at least one case had a generator
  on disk.
* Forbidden-claim audit fires for a generator containing a positive
  claim outside ``not <claim>`` disclaimer form.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from app.services.reporting._schema_versions import (
    COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION,
    TRUST_SCORE_PROVENANCE_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)
from app.services.reporting.trust_score_provenance import (
    PROVENANCE_INPUT_KINDS,
    build_trust_score_provenance,
)


def _seed_case(
    root: Path,
    case_id: str,
    *,
    with_generator: bool = True,
    generator_body: bytes = b"# generator placeholder\nprint('hi')\n",
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


# ---------------------------------------------------------------------
# Schema version + tuple SSOT
# ---------------------------------------------------------------------


def test_provenance_input_kinds_tuple_has_generator_last() -> None:
    assert PROVENANCE_INPUT_KINDS == (
        "metrics",
        "convergence",
        "completeness",
        "reproducibility",
        "generator",
    )
    assert len(PROVENANCE_INPUT_KINDS) == 5
    assert PROVENANCE_INPUT_KINDS[-1] == "generator"


def test_trust_score_provenance_schema_version_is_1_2_0() -> None:
    """Phase 10 E MINOR bump 1.1.0 -> 1.2.0 added three new additive
    fields (``sha256_normalized``, ``normalization_method``,
    ``normalization_error``) to every input row. Old consumers reading
    the 1.1.0 fields continue to work."""
    assert TRUST_SCORE_PROVENANCE_SCHEMA_VERSION == "1.2.0"


def test_cohort_snapshot_manifest_schema_version_is_1_3_0() -> None:
    assert COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION == "1.3.0"


# ---------------------------------------------------------------------
# Snapshot writer side effects
# ---------------------------------------------------------------------


def test_snapshot_writer_creates_generator_subdir(tmp_path: Path) -> None:
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=False)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    assert (tmp_path / "reports" / "snapshots" / "2026-05-16T100000Z" / "generator").is_dir()


def test_snapshot_writer_freezes_generator_bytes_when_present(tmp_path: Path) -> None:
    body = b"# slice 9-B generator\nprint('frozen')\n"
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=True, generator_body=body)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    captured = (
        tmp_path
        / "reports"
        / "snapshots"
        / "2026-05-16T100000Z"
        / "generator"
        / "GS-A-candidate.py"
    )
    assert captured.is_file()
    assert captured.read_bytes() == body


def test_snapshot_writer_skips_generator_when_missing_on_disk(tmp_path: Path) -> None:
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=False)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    captured = (
        tmp_path
        / "reports"
        / "snapshots"
        / "2026-05-16T100000Z"
        / "generator"
        / "GS-A-candidate.py"
    )
    assert not captured.exists()


def test_snapshot_writer_includes_generator_in_members_when_landed(tmp_path: Path) -> None:
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=True)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    manifest_path = (
        tmp_path / "reports" / "snapshots" / "2026-05-16T100000Z" / "SNAPSHOT_MANIFEST.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "generator/GS-A-candidate.py" in manifest["members"]
    assert manifest["schema_version"] == "1.3.0"


def test_snapshot_writer_omits_generator_member_when_missing(tmp_path: Path) -> None:
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=False)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    manifest_path = (
        tmp_path / "reports" / "snapshots" / "2026-05-16T100000Z" / "SNAPSHOT_MANIFEST.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert all("generator/" not in m for m in manifest["members"])


def test_snapshot_writer_refuses_generator_with_forbidden_claim(tmp_path: Path) -> None:
    bad_body = b"# this generator was validated against ASTM E8\n"
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=True, generator_body=bad_body)
    with pytest.raises(ValueError, match="forbidden positive claim"):
        write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")


def test_snapshot_writer_accepts_non_utf8_generator(tmp_path: Path) -> None:
    """A binary / non-UTF-8 generator file must not crash the writer.

    The forbidden-claim audit decodes with errors='replace'; the SHA
    + present=True still ship via the raw bytes."""
    non_utf8 = b"\xff\xfe\x00\x01 binary header\nprint('ok')\n"
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=True, generator_body=non_utf8)
    result = write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    assert "generator/GS-A-candidate.py" in result.members
    captured = (
        tmp_path
        / "reports"
        / "snapshots"
        / "2026-05-16T100000Z"
        / "generator"
        / "GS-A-candidate.py"
    )
    assert captured.read_bytes() == non_utf8


# ---------------------------------------------------------------------
# Provenance walker
# ---------------------------------------------------------------------


def test_provenance_emits_generator_row_present_true_with_sha(tmp_path: Path) -> None:
    body = b"# slice 9-B generator\nprint('hi')\n"
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=True, generator_body=body)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    gen_rows = [i for i in report.inputs if i.kind == "generator"]
    assert len(gen_rows) == 1
    assert gen_rows[0].present is True
    assert gen_rows[0].path == "generator/GS-A-candidate.py"
    assert gen_rows[0].sha256 == hashlib.sha256(body).hexdigest()


def test_provenance_emits_generator_row_present_false_when_missing(tmp_path: Path) -> None:
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=False)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    gen_rows = [i for i in report.inputs if i.kind == "generator"]
    assert len(gen_rows) == 1
    assert gen_rows[0].present is False
    assert gen_rows[0].sha256 is None


def test_provenance_input_order_matches_tuple_ssot(tmp_path: Path) -> None:
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=True)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    walked_kinds = tuple(i.kind for i in report.inputs)
    assert walked_kinds == PROVENANCE_INPUT_KINDS


def test_provenance_emits_schema_version_1_2_0(tmp_path: Path) -> None:
    """Phase 10 E bumped 1.1.0 -> 1.2.0 (additive canonical SHA fields)."""
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=True)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    assert report.schema_version == "1.2.0"


# ---------------------------------------------------------------------
# Forward-compat read: 1.0.0-era snapshot (no generator/ subdir)
# ---------------------------------------------------------------------


def test_provenance_reads_legacy_snapshot_without_generator_dir(tmp_path: Path) -> None:
    """Simulate a pre-Phase-9-B snapshot by writing one and then
    removing the generator/ subdir. The 1.1.0 walker should still
    return cleanly with present=False for the generator row."""
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=True)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    legacy_gen_dir = tmp_path / "reports" / "snapshots" / "2026-05-16T100000Z" / "generator"
    # Wipe the directory to mimic a 1.2.0-era snapshot.
    for entry in legacy_gen_dir.iterdir():
        entry.unlink()
    legacy_gen_dir.rmdir()
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    gen_rows = [i for i in report.inputs if i.kind == "generator"]
    assert len(gen_rows) == 1
    assert gen_rows[0].present is False
    assert gen_rows[0].sha256 is None


# ---------------------------------------------------------------------
# Tier 1 disclaimer trio preserved across the bump
# ---------------------------------------------------------------------


def test_provenance_envelope_carries_tier1_disclaimer_trio(tmp_path: Path) -> None:
    case = _seed_case(tmp_path, "GS-A-candidate", with_generator=True)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    assert report.claim_tier == "Tier 1 engineering candidate"
    assert "not signed validation" in report.claim_impact
    assert "not benchmark agreement" in report.claim_impact
