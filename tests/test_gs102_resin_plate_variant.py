import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "gs102_prepare_resin_plate_variant.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("gs102_prepare_resin_plate_variant", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


DECK = "\n".join(
    [
        "/MAT/PLAS_JOHNS/1",
        "projectile_steel_hardened_candidate",
        "# projectile remains unchanged",
        "/MAT/PLAS_JOHNS/2",
        "weldox_460E_plate_candidate",
        "#              RHO_I",
        "              7.85E-6                   0",
        "#                  E                  Nu     Iflag",
        "                 200                  .33         0",
        (
            "#                  a                   b                   n"
            "           EPS_p_max            SIG_max0"
        ),
        (
            "                 490                 383                 .45"
            "                 0.3                   0"
        ),
        (
            "#                  c           EPS_DOT_0       ICC"
            "   Fsmooth               F_cut               Chard"
        ),
        "              0.0114                5.E-4         0         0"
        "                   0                   0",
        "#                  m              T_melt              rhoC_p                 T_r",
        "                 .94                1800                   0                 293",
        "/FAIL/JOHNSON/2",
        (
            "#                 D1                  D2                  D3"
            "                  D4                  D5"
        ),
        "              0.0705               1.732                -.54               -.015"
        "                   0",
        (
            "#      EPSILON_DOT_0  IFAIL_SH  IFAIL_SO"
            "            EPSF_MIN                DADV               IXFEM"
        ),
        "                .001         2         1                   0"
        "                   0                    0",
        "#-  2. NODES",
        "",
    ]
)


def test_resin_plate_deck_keeps_projectile_and_replaces_plate_material() -> None:
    module = _load_module()

    patched = module.make_resin_plate_deck(DECK)

    assert "projectile_steel_hardened_candidate" in patched
    assert "generic_resin_plate_visual_candidate" in patched
    assert "weldox_460E_plate_candidate" not in patched
    assert "1.20E-6" in patched
    assert "not signed validation" in module.CLAIM_BOUNDARY


def test_prepare_resin_variant_writes_only_project_state(tmp_path: Path) -> None:
    module = _load_module()
    source_dir = tmp_path / "golden_samples" / "source" / "data"
    source_dir.mkdir(parents=True)
    (source_dir / "model_00_0000.rad").write_text(DECK, encoding="utf-8")
    (source_dir / "model_00_0001.rad").write_text("/END\n", encoding="utf-8")
    output_dir = tmp_path / "project_state" / "diagnostic_sources" / "resin" / "data"

    manifest = module.prepare_resin_variant(
        module.ResinVariantConfig(
            repo_root=tmp_path,
            source_case_dir=source_dir,
            output_case_dir=output_dir,
        )
    )

    assert (output_dir / "model_00_0000.rad").exists()
    assert (output_dir / "model_00_0001.rad").exists()
    assert manifest["output_case_dir"] == "project_state/diagnostic_sources/resin/data"
    assert "golden_samples" not in manifest["output_case_dir"]


def test_prepare_resin_variant_rejects_golden_sample_output(tmp_path: Path) -> None:
    module = _load_module()

    try:
        module.prepare_resin_variant(
            module.ResinVariantConfig(
                repo_root=tmp_path,
                source_case_dir=tmp_path / "source",
                output_case_dir=tmp_path / "golden_samples" / "bad" / "data",
            )
        )
    except ValueError as exc:
        assert "golden_samples" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected golden_samples output rejection")
