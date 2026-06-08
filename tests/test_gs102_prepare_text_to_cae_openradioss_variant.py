import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "gs102_prepare_text_to_cae_openradioss_variant.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "gs102_prepare_text_to_cae_openradioss_variant",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


STARTER = """# GS-102-refined-candidate / FM-04a Tier 1 ballistic candidate (REFINED mesh)
#   * Refined mesh demonstrates JC damage element-deletion kinematics in the
#     impact zone. Still NOT validated against Borvik 2002; NOT benchmark-quality.
#   * Materials, JC params, BCS clamp, contact, INIVEL all carried over from
#     GS-102-candidate verbatim.
/TITLE
GS-102-refined-candidate Tier 1 perforation demo (Borvik 2002 params, NOT validated)
/BEGIN
gs102_refined_candidate
/INIVEL/TRA/1
projectile_initial_velocity_candidate
#                 Vx                  Vy                  Vz   Gnod_id   Skew_id
                 150                   0                   0       100         0
/END
"""


ENGINE = """/RUN/gs102_refined_candidate/1/
  0.15
# Frame cadence: 150 frames over 0.15 ms run (frame every 0.001 ms).
# At V0=150 m/s the impact + perforation + plug-ejection is captured
# in this window.
/ANIM/DT
0.0  0.001
/ANIM/VECT/VEL
"""


def test_load_text_to_cae_parameters_clamps_ranges(tmp_path: Path) -> None:
    module = _load_module()
    params = tmp_path / "cae_parameters.json"
    params.write_text(
        json.dumps(
            {
                "plate_length_mm": 999.0,
                "bullet_diameter_mm": 10.0,
                "bullet_length_mm": 15.0,
                "impact_velocity_mps": 5000.0,
                "output_frames": 999,
            }
        ),
        encoding="utf-8",
    )

    loaded = module.load_text_to_cae_parameters(params)

    assert loaded["plate_length_mm"] == 350.0
    assert loaded["bullet_length_mm"] == 20.0
    assert loaded["impact_velocity_mps"] == 1800.0
    assert loaded["output_frames"] == 600


def test_patch_starter_and_engine_map_velocity_time_and_frames() -> None:
    module = _load_module()
    parameters = module.load_text_to_cae_parameters(None)

    starter = module.patch_starter_for_text_to_cae(STARTER, parameters)
    engine = module.patch_engine_for_text_to_cae(ENGINE, parameters)

    assert "GS-102-text-to-cae-openradioss-v1" in starter
    assert "NOT full-size geometry" in starter
    assert "830" in starter
    assert "gs102_text_to_cae_openradioss_v1" in engine
    assert "0.08" in engine
    assert "0.000333333333333" in engine
    assert "impact_time_s=8e-05" in engine


def test_prepare_text_to_cae_variant_writes_project_state_manifest(tmp_path: Path) -> None:
    module = _load_module()
    source_dir = tmp_path / "golden_samples" / "source" / "data"
    source_dir.mkdir(parents=True)
    (source_dir / "model_00_0000.rad").write_text(STARTER, encoding="utf-8")
    (source_dir / "model_00_0001.rad").write_text(ENGINE, encoding="utf-8")
    output_dir = tmp_path / "project_state" / "diagnostic_sources" / "text-to-cae" / "data"

    manifest = module.prepare_text_to_cae_openradioss_variant(
        module.TextToCaeVariantConfig(
            repo_root=tmp_path,
            source_case_dir=source_dir,
            output_case_dir=output_dir,
            parameters_json=None,
        )
    )

    assert (output_dir / "model_00_0000.rad").exists()
    assert (output_dir / "model_00_0001.rad").exists()
    assert manifest["recipe_id"] == "openradioss_bullet_plate_candidate.v1"
    assert manifest["output_case_dir"] == "project_state/diagnostic_sources/text-to-cae/data"
    assert "impact_velocity_mps" in manifest["mapped_parameters"]
    assert "plate_length_mm" in manifest["intent_only_parameters"]


def test_prepare_text_to_cae_variant_rejects_golden_sample_output(tmp_path: Path) -> None:
    module = _load_module()

    try:
        module.prepare_text_to_cae_openradioss_variant(
            module.TextToCaeVariantConfig(
                repo_root=tmp_path,
                source_case_dir=tmp_path / "source",
                output_case_dir=tmp_path / "golden_samples" / "bad" / "data",
                parameters_json=None,
            )
        )
    except ValueError as exc:
        assert "golden_samples" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected golden_samples output rejection")
