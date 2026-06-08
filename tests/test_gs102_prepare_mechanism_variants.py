import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "gs102_prepare_mechanism_variants.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "gs102_prepare_mechanism_variants",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _seed_source(source: Path) -> None:
    source.mkdir(parents=True)
    (source / "model_00_0000.rad").write_text(
        "\n".join(
            [
                "/MAT/PLAS_JOHNS/2",
                (
                    "                 490                 383                 .45"
                    "                 0.3                   0"
                ),
                "/INTER/TYPE7/1",
                (
                    "                   0                   0                  .1"
                    "                   0                   0"
                ),
            ]
        ),
        encoding="utf-8",
    )
    (source / "model_00_0001.rad").write_text(
        "/ANIM/DT\n0.0  0.001\n/DT/NODA/CST/0\n0.9 0.0\n",
        encoding="utf-8",
    )


def test_prepare_mechanism_variants_writes_project_state_only(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = tmp_path / "repo"
    source = repo_root / "golden_samples" / "GS-102-refined-candidate" / "data"
    output_root = repo_root / "project_state" / "diagnostic_sources"
    _seed_source(source)

    prepared = module.prepare_mechanism_variants(
        repo_root=repo_root,
        source_case_dir=source,
        output_root=output_root,
        variant_keys=[
            "cfl_080",
            "cfl_085",
            "cfl_095",
            "cfl_100",
            "anim_dt_0005",
            "plate_epspmax_045",
            "contact_fric_005",
            "cfl_045",
        ],
    )

    assert len(prepared) == 8
    for variant_dir in prepared:
        assert "project_state" in variant_dir.relative_to(repo_root).parts
        assert "golden_samples" not in variant_dir.relative_to(repo_root).parts
        manifest = json.loads(
            (variant_dir.parent / "diagnostic_variant.json").read_text(encoding="utf-8")
        )
        assert "not_signed_validation" in manifest["claim_boundary"]
        assert manifest["replacements"]

    cfl080_text = prepared[0].joinpath("model_00_0001.rad").read_text(encoding="utf-8")
    cfl085_text = prepared[1].joinpath("model_00_0001.rad").read_text(encoding="utf-8")
    cfl095_text = prepared[2].joinpath("model_00_0001.rad").read_text(encoding="utf-8")
    cfl100_text = prepared[3].joinpath("model_00_0001.rad").read_text(encoding="utf-8")
    anim_text = prepared[4].joinpath("model_00_0001.rad").read_text(encoding="utf-8")
    eps_text = prepared[5].joinpath("model_00_0000.rad").read_text(encoding="utf-8")
    fric_text = prepared[6].joinpath("model_00_0000.rad").read_text(encoding="utf-8")
    cfl045_text = prepared[7].joinpath("model_00_0001.rad").read_text(encoding="utf-8")
    assert "0.8 0.0" in cfl080_text
    assert "0.85 0.0" in cfl085_text
    assert "0.95 0.0" in cfl095_text
    assert "1.0 0.0" in cfl100_text
    assert "0.0  0.0005" in anim_text
    assert "0.45                   0" in eps_text
    assert ".05                  .1" in fric_text
    assert "0.45 0.0" in cfl045_text

    source_text = (source / "model_00_0000.rad").read_text(encoding="utf-8")
    assert "                 0.3                   0" in source_text


def test_prepare_mechanism_variants_rejects_golden_output(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = tmp_path / "repo"
    source = repo_root / "golden_samples" / "GS-102-refined-candidate" / "data"
    _seed_source(source)

    with pytest.raises(ValueError, match="golden_samples"):
        module.prepare_mechanism_variants(
            repo_root=repo_root,
            source_case_dir=source,
            output_root=repo_root / "golden_samples" / "bad",
            variant_keys=["cfl_045"],
        )
