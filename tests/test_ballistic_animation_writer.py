"""Tests for ballistics.animation_writer — Tier 1 candidate side-view GIF.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.ballistics import (  # noqa: E402
    BallisticAnimationInput,
    BallisticTimeSample,
    write_ballistic_animation,
)
from app.services.ballistics.animation_writer import (  # noqa: E402
    _build_timeline,
    _position_and_velocity_at,
)


def _two_sample_input(case_id: str = "CASE-FM04A-ANIM-TEST") -> BallisticAnimationInput:
    samples = [
        BallisticTimeSample(t_s=0.0, position_m=(-0.05, 0, 0), velocity_m_per_s=(285.0, 0, 0)),
        BallisticTimeSample(t_s=2.0e-4, position_m=(0.06, 0, 0), velocity_m_per_s=(142.0, 0, 0)),
    ]
    return BallisticAnimationInput(
        case_id=case_id,
        samples=samples,
        plate_back_face_x_m=0.012,
        plate_thickness_m=0.012,
    )


def test_writer_produces_gif_and_manifest(tmp_path: Path) -> None:
    out = write_ballistic_animation(_two_sample_input(), tmp_path, frames=12)
    assert out.name == "animation_manifest.json"
    assert out.exists()
    gif = tmp_path / "candidate_animation.gif"
    assert gif.exists()


def test_gif_has_expected_frame_count(tmp_path: Path) -> None:
    write_ballistic_animation(_two_sample_input(), tmp_path, frames=15)
    gif = tmp_path / "candidate_animation.gif"
    im = Image.open(gif)
    n = 1
    try:
        while True:
            im.seek(im.tell() + 1)
            n += 1
    except EOFError:
        pass
    assert n == 15


def test_manifest_records_kinematic_phases(tmp_path: Path) -> None:
    write_ballistic_animation(_two_sample_input(), tmp_path, frames=30)
    manifest = json.loads((tmp_path / "animation_manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "fm04a-ballistic-animation-manifest.v1"
    assert manifest["kinematics"]["v0_m_per_s"] == 285.0
    assert manifest["kinematics"]["vr_m_per_s"] == 142.0
    # Pre/cross/post all populated and positive
    assert manifest["kinematics"]["t_pre_impact_s"] > 0
    assert manifest["kinematics"]["t_crossing_s"] > 0
    assert manifest["kinematics"]["t_post_impact_s"] > 0
    # Perforation must occur at some frame inside the GIF
    perf_frame = manifest["kinematics"]["perforated_at_frame"]
    assert perf_frame is not None
    assert 0 <= perf_frame < 30


def test_manifest_carries_tier1_wording(tmp_path: Path) -> None:
    write_ballistic_animation(_two_sample_input(), tmp_path, frames=10)
    raw = (tmp_path / "animation_manifest.json").read_text(encoding="utf-8")
    assert "tier1_engineering_candidate" in raw
    assert "not_signed_validation" in raw
    assert "not_benchmark_agreement" in raw
    # No bare affirmative overclaim wording
    lower = raw.lower()
    for phrase in ("validated physics", "perforation completed", "bullet-through-steel complete"):
        assert phrase not in lower


def test_artifact_block_has_sha256_and_size(tmp_path: Path) -> None:
    write_ballistic_animation(_two_sample_input(), tmp_path, frames=8)
    manifest = json.loads((tmp_path / "animation_manifest.json").read_text(encoding="utf-8"))
    art = manifest["artifact"]
    assert art["kind"] == "ballistic_animation_gif"
    assert art["file_name"] == "candidate_animation.gif"
    assert art["size_bytes"] > 0
    assert len(art["sha256"]) == 64


def test_writer_rejects_empty_samples(tmp_path: Path) -> None:
    bad = BallisticAnimationInput(
        case_id="X",
        samples=[],
        plate_back_face_x_m=0.012,
        plate_thickness_m=0.012,
    )
    with pytest.raises(ValueError, match="samples must not be empty"):
        write_ballistic_animation(bad, tmp_path)


def test_writer_rejects_zero_thickness(tmp_path: Path) -> None:
    bad = BallisticAnimationInput(
        case_id="X",
        samples=[
            BallisticTimeSample(t_s=0.0, position_m=(0, 0, 0), velocity_m_per_s=(285, 0, 0)),
        ],
        plate_back_face_x_m=0.012,
        plate_thickness_m=0.0,
    )
    with pytest.raises(ValueError, match="plate_thickness_m must be > 0"):
        write_ballistic_animation(bad, tmp_path)


def test_writer_rejects_too_few_frames(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="frames must be >= 2"):
        write_ballistic_animation(_two_sample_input(), tmp_path, frames=1)


def test_position_at_t_pre_matches_v0_motion() -> None:
    tl = _build_timeline(v0=285.0, vr=142.0, x_start=-0.05, plate_front=0.0, plate_back=0.012)
    # Halfway through the pre-impact phase: x = x_start + v0 * (t_pre/2)
    half_pre = tl.t_pre / 2.0
    x, v = _position_and_velocity_at(half_pre, tl)
    assert v == pytest.approx(285.0)
    assert x == pytest.approx(-0.05 + 285.0 * half_pre, rel=1e-9)


def test_position_after_crossing_uses_residual_velocity() -> None:
    tl = _build_timeline(v0=285.0, vr=142.0, x_start=-0.05, plate_front=0.0, plate_back=0.012)
    t_just_after_cross = tl.t_pre + tl.t_cross + 1e-7
    x, v = _position_and_velocity_at(t_just_after_cross, tl)
    assert v == pytest.approx(142.0)
    # Position should be just past the back face
    assert x >= 0.012


def test_pipeline_integration_writes_animation_into_runtime(tmp_path: Path) -> None:
    """Smoke: invoking pipeline main with --write-animation lands the GIF + manifest."""
    import importlib.util

    pipeline_path = REPO_ROOT / "scripts" / "fm04a_synthetic_pipeline.py"
    gs001_frd = REPO_ROOT / "golden_samples" / "GS-001" / "gs001_result.frd"
    backend_app = REPO_ROOT / "backend" / "app"
    if not gs001_frd.exists() or not backend_app.exists():
        pytest.skip("required real-repo fixtures missing")

    fake_repo = tmp_path / "fake_repo"
    (fake_repo / "golden_samples" / "GS-001").mkdir(parents=True)
    (fake_repo / "golden_samples" / "GS-001" / "gs001_result.frd").symlink_to(gs001_frd)
    (fake_repo / "backend").mkdir()
    (fake_repo / "backend" / "app").symlink_to(backend_app)

    spec = importlib.util.spec_from_file_location("fm04a_synthetic_pipeline", pipeline_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("fm04a_synthetic_pipeline", mod)
    spec.loader.exec_module(mod)

    rc = mod.main(
        [
            "--repo-root",
            str(fake_repo),
            "--case-id",
            "CASE-FM04A-ANIM-PIPE",
            "--write-animation",
        ]
    )
    assert rc == 0

    ballistic_dir = (
        fake_repo / "project_state" / "graph_executor" / "CASE-FM04A-ANIM-PIPE" / "ballistic"
    )
    assert (ballistic_dir / "animation_manifest.json").exists()
    assert (ballistic_dir / "candidate_animation.gif").exists()
