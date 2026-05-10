"""Tests for structural_animation — render a real CalculiX FRD as GIF.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
import sys
from itertools import pairwise
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.parsers.frd_parser import FRDParser  # noqa: E402
from app.services.structural_animation import (  # noqa: E402
    FRDAnimationInput,
    write_frd_deformation_animation,
)

GS001_FRD = REPO_ROOT / "golden_samples" / "GS-001" / "gs001_result.frd"


def _real_result():
    if not GS001_FRD.exists():
        pytest.skip(f"GS-001 FRD fixture missing at {GS001_FRD}")
    return FRDParser().parse(str(GS001_FRD))


def test_writer_produces_gif_and_manifest_from_real_frd(tmp_path: Path) -> None:
    result = _real_result()
    out = write_frd_deformation_animation(
        result,
        FRDAnimationInput(
            case_id="GS-001-TEST",
            frd_source_path=str(GS001_FRD),
            deformation_scale=10.0,
        ),
        tmp_path,
        frames=8,
    )
    assert out.name == "deformation_animation_manifest.json"
    assert out.exists()
    assert (tmp_path / "deformation_animation.gif").exists()


def test_gif_has_expected_frame_count(tmp_path: Path) -> None:
    result = _real_result()
    write_frd_deformation_animation(
        result,
        FRDAnimationInput(case_id="GS-001-TEST", frd_source_path=str(GS001_FRD)),
        tmp_path,
        frames=12,
    )
    im = Image.open(tmp_path / "deformation_animation.gif")
    n = 1
    try:
        while True:
            im.seek(im.tell() + 1)
            n += 1
    except EOFError:
        pass
    assert n == 12


def test_manifest_records_real_provenance(tmp_path: Path) -> None:
    """The manifest's source_provenance MUST reflect the actual parsed
    FRD topology + the real target-increment metadata. This is the
    "no fabrication" guarantee — the rendered animation comes from
    the same FRD the manifest cites."""
    result = _real_result()
    write_frd_deformation_animation(
        result,
        FRDAnimationInput(
            case_id="GS-001-PROV",
            frd_source_path=str(GS001_FRD),
            deformation_scale=10.0,
        ),
        tmp_path,
        frames=6,
    )
    manifest = json.loads(
        (tmp_path / "deformation_animation_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["schema_version"] == "structural-deformation-animation-manifest.v1"
    assert manifest["source_file"] == str(GS001_FRD)

    prov = manifest["source_provenance"]
    assert prov["parser"] == "FRDParser"
    assert prov["node_count"] == len(result.nodes)
    assert prov["element_count"] == len(result.elements)
    assert prov["increment_count"] == len(result.increments)
    # GS-001 has displacements on inc[0] and stresses on inc[1]
    assert prov["target_increment_index"] == 1
    assert prov["target_increment_has_displacements"] is True
    assert prov["stress_source_increment_index"] == 2
    # max_displacement_target reflects the actual FRD value, not a fabricated number
    target_inc = next(inc for inc in result.increments if inc.displacements)
    assert manifest["max_displacement_target_units"] == pytest.approx(target_inc.max_displacement)


def test_max_disp_per_frame_is_monotonic(tmp_path: Path) -> None:
    """Pseudo-time interpolation is linear; per-frame max |disp| must
    therefore be monotonic non-decreasing from 0 to the FRD's
    max_displacement value."""
    result = _real_result()
    write_frd_deformation_animation(
        result,
        FRDAnimationInput(
            case_id="GS-001-MONO",
            frd_source_path=str(GS001_FRD),
            deformation_scale=1.0,
        ),
        tmp_path,
        frames=10,
    )
    manifest = json.loads(
        (tmp_path / "deformation_animation_manifest.json").read_text(encoding="utf-8")
    )
    series = manifest["max_displacement_per_frame_units"]
    assert series[0] == pytest.approx(0.0)
    assert series[-1] == pytest.approx(manifest["max_displacement_target_units"])
    for prev, curr in pairwise(series):
        assert curr >= prev - 1e-9


def test_manifest_carries_tier1_wording(tmp_path: Path) -> None:
    result = _real_result()
    write_frd_deformation_animation(
        result,
        FRDAnimationInput(case_id="GS-001-WORD", frd_source_path=str(GS001_FRD)),
        tmp_path,
        frames=6,
    )
    raw = (tmp_path / "deformation_animation_manifest.json").read_text(encoding="utf-8")
    assert "tier1_engineering_candidate" in raw
    assert "not_signed_validation" in raw
    assert "not_benchmark_agreement" in raw
    # No bare overclaim wording
    lower = raw.lower()
    for phrase in (
        "validated physics",
        "perforation completed",
        "bullet-through-steel complete",
    ):
        assert phrase not in lower


def test_artifact_block_has_sha256(tmp_path: Path) -> None:
    result = _real_result()
    write_frd_deformation_animation(
        result,
        FRDAnimationInput(case_id="GS-001-SHA", frd_source_path=str(GS001_FRD)),
        tmp_path,
        frames=6,
    )
    manifest = json.loads(
        (tmp_path / "deformation_animation_manifest.json").read_text(encoding="utf-8")
    )
    art = manifest["artifact"]
    assert art["kind"] == "structural_deformation_animation_gif"
    assert art["file_name"] == "deformation_animation.gif"
    assert len(art["sha256"]) == 64
    assert art["size_bytes"] > 0


def test_writer_rejects_too_few_frames(tmp_path: Path) -> None:
    result = _real_result()
    with pytest.raises(ValueError, match="frames must be >= 2"):
        write_frd_deformation_animation(
            result,
            FRDAnimationInput(case_id="X", frd_source_path=str(GS001_FRD)),
            tmp_path,
            frames=1,
        )


def test_writer_rejects_empty_increments(tmp_path: Path) -> None:
    result = _real_result()
    # Mutate to simulate a parse with no increments
    object.__setattr__(result, "increments", [])
    with pytest.raises(ValueError, match="no increments"):
        write_frd_deformation_animation(
            result,
            FRDAnimationInput(case_id="X", frd_source_path=str(GS001_FRD)),
            tmp_path,
        )


def test_bounding_box_recorded(tmp_path: Path) -> None:
    result = _real_result()
    write_frd_deformation_animation(
        result,
        FRDAnimationInput(
            case_id="GS-001-BBOX",
            frd_source_path=str(GS001_FRD),
            deformation_scale=1.0,
        ),
        tmp_path,
        frames=6,
    )
    manifest = json.loads(
        (tmp_path / "deformation_animation_manifest.json").read_text(encoding="utf-8")
    )
    bbox = manifest["bounding_box"]
    # GS-001 mesh extends 0..100 mm in x, 0..10 mm in y at undeformed.
    # Bbox is computed from the union of undeformed + final-deformed
    # node positions, so it can extend slightly beyond the reference
    # mesh by the magnitude of the boundary nodes' displacement.
    assert bbox["x_min"] <= 0.0
    assert 100.0 <= bbox["x_max"] <= 101.0
    assert bbox["y_min"] <= 0.0
    assert bbox["y_max"] >= 10.0
