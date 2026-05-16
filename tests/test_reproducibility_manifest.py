"""Tests for the Tier 1 reproducibility manifest (FM-04a Phase 5 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

import pytest
from app.services.reporting._schema_versions import (
    REPRODUCIBILITY_MANIFEST_SCHEMA_VERSION,
)
from app.services.reporting.reproducibility_manifest import (
    CLAIM_TIER,
    ReproducibilityManifestInputs,
    build_reproducibility_manifest,
    render_reproducibility_manifest_json,
    write_reproducibility_manifest,
)


def _init_git_repo(repo_root: Path) -> None:
    """Initialize a minimal git repo so the builder captures commit/branch."""
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(repo_root)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.email", "phase5b@example.test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.name", "Phase 5 B"],
        check=True,
        capture_output=True,
    )
    seed = repo_root / "seed.txt"
    seed.write_text("phase 5 B seed\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo_root), "add", str(seed)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "commit", "-q", "-m", "seed for phase 5 B test"],
        check=True,
        capture_output=True,
    )


def test_builder_stamps_schema_version(tmp_path: Path) -> None:
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(case_id="GS-102-repro-stamp", repo_root=tmp_path)
    )
    rendered = json.loads(render_reproducibility_manifest_json(manifest))
    assert rendered["schema_version"] == REPRODUCIBILITY_MANIFEST_SCHEMA_VERSION


def test_builder_captures_python_and_platform(tmp_path: Path) -> None:
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(case_id="GS-102-repro-stamp", repo_root=tmp_path)
    )
    assert manifest.python_version == platform.python_version()
    assert manifest.python_implementation == platform.python_implementation()
    assert manifest.platform_summary
    assert manifest.claim_tier == CLAIM_TIER


def test_builder_captures_git_state_when_repo_present(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(case_id="GS-102-repro-stamp", repo_root=tmp_path)
    )
    assert manifest.git_commit_sha is not None
    assert len(manifest.git_commit_sha) == 40
    assert manifest.git_branch in {"main", "master"}
    assert manifest.git_dirty is False


def test_builder_marks_git_dirty_when_working_tree_modified(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "seed.txt").write_text("modified\n", encoding="utf-8")
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(case_id="GS-102-repro-stamp", repo_root=tmp_path)
    )
    assert manifest.git_dirty is True


def test_builder_handles_missing_git_directory(tmp_path: Path) -> None:
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(case_id="GS-102-repro-stamp", repo_root=tmp_path)
    )
    assert manifest.git_commit_sha is None
    assert manifest.git_branch is None
    assert manifest.git_dirty is False


def test_builder_fingerprints_generator_script(tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "gen_gs102_deck.py"
    script.parent.mkdir(parents=True)
    script.write_bytes(b"# generator placeholder\nprint('hello')\n")
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(
            case_id="GS-102-repro-stamp",
            repo_root=tmp_path,
            generator_script_path=script,
        )
    )
    assert len(manifest.scripts) == 1
    fp = manifest.scripts[0]
    assert fp.relpath == "scripts/gen_gs102_deck.py"
    assert len(fp.sha256) == 64
    assert fp.bytes_count == len(b"# generator placeholder\nprint('hello')\n")


def test_builder_omits_missing_scripts(tmp_path: Path) -> None:
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(
            case_id="GS-102-repro-stamp",
            repo_root=tmp_path,
            generator_script_path=tmp_path / "scripts" / "missing.py",
        )
    )
    assert manifest.scripts == []


def test_builder_dedupes_script_paths(tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "shared.py"
    script.parent.mkdir(parents=True)
    script.write_bytes(b"shared\n")
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(
            case_id="GS-102-repro-stamp",
            repo_root=tmp_path,
            generator_script_path=script,
            additional_script_paths=(script,),
        )
    )
    assert len(manifest.scripts) == 1


def test_builder_lists_tracked_packages(tmp_path: Path) -> None:
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(case_id="GS-102-repro-stamp", repo_root=tmp_path)
    )
    names = {p.name for p in manifest.tracked_packages}
    assert "fastapi" in names
    assert "numpy" in names
    # fastapi must be installed in this venv; expect a version, not 'not_installed'
    fastapi_pkg = next(p for p in manifest.tracked_packages if p.name == "fastapi")
    assert fastapi_pkg.version != "not_installed"


def test_builder_preserves_tier1_blockers(tmp_path: Path) -> None:
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(case_id="GS-102-repro-stamp", repo_root=tmp_path)
    )
    assert any("FM-04b P8" in blocker for blocker in manifest.tier2_blockers_remaining)
    assert any("ADR-024" in blocker for blocker in manifest.tier2_blockers_remaining)


def test_writer_refuses_golden_samples(tmp_path: Path) -> None:
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(case_id="GS-102-repro-stamp", repo_root=tmp_path)
    )
    forbidden = tmp_path / "golden_samples" / "GS-102-candidate"
    with pytest.raises(ValueError, match="golden_samples"):
        write_reproducibility_manifest(manifest, forbidden)


def test_writer_succeeds_under_reports(tmp_path: Path) -> None:
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(case_id="GS-102-repro-stamp", repo_root=tmp_path)
    )
    out_dir = tmp_path / "reports" / "GS-102-candidate"
    out_path = write_reproducibility_manifest(manifest, out_dir)
    assert out_path.is_file()
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["case_id"] == "GS-102-repro-stamp"
    assert loaded["schema_version"] == REPRODUCIBILITY_MANIFEST_SCHEMA_VERSION


def test_builder_rejects_forbidden_claim_injection(tmp_path: Path) -> None:
    # Inject a forbidden claim into a script body and ensure the audit
    # does NOT flag it (the audit only inspects the rendered manifest,
    # not script *contents*; this protects against the SHA being
    # interpreted as text). The script body never enters the manifest
    # haystack; only its hash + relpath do.
    script = tmp_path / "scripts" / "evil.py"
    script.parent.mkdir(parents=True)
    script.write_text("# benchmark agreement was reached here\n", encoding="utf-8")
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(
            case_id="GS-102-repro-stamp",
            repo_root=tmp_path,
            generator_script_path=script,
        )
    )
    rendered = render_reproducibility_manifest_json(manifest)
    # The forbidden phrase from the script body must NOT have leaked
    # into the manifest JSON (we only stored the hash + path).
    assert "benchmark agreement was reached" not in rendered.lower()


def test_claim_tier_disclaimer_is_preserved(tmp_path: Path) -> None:
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(case_id="GS-102-repro-stamp", repo_root=tmp_path)
    )
    rendered = render_reproducibility_manifest_json(manifest)
    assert "not signed validation" in rendered
    assert "not benchmark agreement" in rendered
