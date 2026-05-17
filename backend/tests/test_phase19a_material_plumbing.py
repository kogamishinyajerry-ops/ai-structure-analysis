"""FM-04a Phase 19 A — material_id end-to-end plumbing tests.

Pins:

* **M:-1** material lookup goes through the SSOT
  ``app.services.materials.get_material``; no inline lookup or
  duplication of property values.
* **T:-3** end-to-end load-bearing pin (``requires_solver``): aluminium
  pick produces a measurably different ``disp.at_nodes()`` than
  steel (E is 3× lower → displacement ~3× higher under same load).
  The test asserts the ratio explicitly.
* **C:-1** rendered audit on the result carries the chosen material's
  reference citation (so the reviewer sees what was used).
* **A:-2** unknown material_id raises a structured
  :class:`Tier2PipelineError` with `stage='resolve_material'`.

Phase 19 A is additive — the existing Phase 1-17 ``SolverService``
async-streaming path is untouched. Tier 2 candidate runs go through
:func:`run_tier2_minimal_hex`; the existing /solver/run route
remains as the default for legacy cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.adapters.calculix import DEFAULT_STEEL, MinimalHexMaterial
from app.services.materials import get_material
from app.services.tier2_pipeline import (
    Tier2PipelineError,
    Tier2RunResult,
    material_reference_for_audit,
    material_to_hex_descriptor,
    resolve_material,
    run_tier2_minimal_hex,
)

LOCAL_CCX_BINARY = "/opt/homebrew/bin/ccx"


# ---------------------------------------------------------------------
# M:-1 — material lookup goes through the SSOT
# ---------------------------------------------------------------------


def test_resolve_material_returns_default_steel_on_none() -> None:
    """Back-compat: when material_id is omitted, Phase 18 A default
    steel is used (no Material lookup attempted)."""
    result = resolve_material(None)
    assert isinstance(result, MinimalHexMaterial)
    assert result is DEFAULT_STEEL


def test_resolve_material_returns_default_on_empty_string() -> None:
    """Empty-string id treated identically to None (the frontend may
    send `material_id: ""` when nothing is picked)."""
    result = resolve_material("")
    assert result is DEFAULT_STEEL


@pytest.mark.parametrize(
    "material_id,expected_e_pa,expected_nu",
    [
        ("steel-s355", 210e9, 0.3),
        ("aluminium-6061-t6", 68.9e9, 0.33),
        ("titanium-ti-6al-4v", 113.8e9, 0.342),
    ],
)
def test_resolve_material_finds_library_entry(
    material_id: str, expected_e_pa: float, expected_nu: float
) -> None:
    """Each baseline library entry round-trips: resolve_material →
    SSOT lookup → pinned values match."""
    mat = resolve_material(material_id)
    # The Material dataclass exposes youngs_modulus_pa + poisson_ratio.
    assert mat.youngs_modulus_pa == expected_e_pa
    assert mat.poisson_ratio == expected_nu
    # And it's identity-equal to a direct get_material call (SSOT).
    direct = get_material(material_id)
    assert mat == direct


def test_resolve_material_raises_pipeline_error_on_unknown() -> None:
    """A:-2 — unknown material_id surfaces a structured
    Tier2PipelineError, NOT a bare KeyError, with stage tag."""
    with pytest.raises(Tier2PipelineError) as excinfo:
        resolve_material("imaginarium-9000")
    assert excinfo.value.stage == "resolve_material"
    assert "imaginarium-9000" in str(excinfo.value)
    assert excinfo.value.cause is not None


# ---------------------------------------------------------------------
# Material → MinimalHexMaterial adapter
# ---------------------------------------------------------------------


def test_material_to_hex_descriptor_preserves_default_steel() -> None:
    out = material_to_hex_descriptor(DEFAULT_STEEL)
    assert out is DEFAULT_STEEL  # pass-through


def test_material_to_hex_descriptor_converts_library_material() -> None:
    al = get_material("aluminium-6061-t6")
    out = material_to_hex_descriptor(al)
    assert isinstance(out, MinimalHexMaterial)
    assert out.youngs_modulus_pa == al.youngs_modulus_pa
    assert out.poisson_ratio == al.poisson_ratio
    # The CalculiX label canonicalises hyphens → underscores +
    # upper-case so the *MATERIAL block ID is valid.
    assert out.name == "ALUMINIUM_6061_T6"
    assert "-" not in out.name


# ---------------------------------------------------------------------
# C:-1 — audit reference for the reviewer
# ---------------------------------------------------------------------


def test_audit_reference_for_default_steel_is_inline_description() -> None:
    ref = material_reference_for_audit(DEFAULT_STEEL)
    assert "Phase 18 A inline default" in ref
    assert "STEEL_S355" in ref
    assert ref.strip() != ""


def test_audit_reference_for_library_material_carries_citation() -> None:
    al = get_material("aluminium-6061-t6")
    ref = material_reference_for_audit(al)
    assert ref == al.reference
    assert "MMPDS-2023" in ref


# ---------------------------------------------------------------------
# INP composition with library material (no solver needed)
# ---------------------------------------------------------------------


def test_tier2_pipeline_writes_inp_with_picked_material_name(
    tmp_path: Path,
) -> None:
    """The composed INP carries the picked material's name AND its
    pinned (E, ν) values written byte-identical from the library."""
    case_dir = tmp_path / "phase19a-inp-shape-candidate"
    case_dir.mkdir()
    # We can't run ccx in the default sweep; intercept by using a
    # non-existent binary so the runner raises after the INP is written.
    with pytest.raises(Tier2PipelineError) as excinfo:
        run_tier2_minimal_hex(
            case_dir,
            jobname="ti",
            material_id="titanium-ti-6al-4v",
            ccx_binary="/path/does/not/exist/ccx",
            timeout_sec=5.0,
        )
    # The error came from run_ccx, AFTER the INP was written.
    assert excinfo.value.stage == "run_ccx"

    inp_path = case_dir / "ti.inp"
    assert inp_path.is_file()
    body = inp_path.read_text(encoding="utf-8")
    # Material name canonicalised + composed *MATERIAL block
    assert "*MATERIAL, NAME=TITANIUM_TI_6AL_4V" in body
    # Pinned values byte-identical to library.json
    ti = get_material("titanium-ti-6al-4v")
    assert f"{ti.youngs_modulus_pa:.6e}" in body
    assert f"{ti.poisson_ratio:.6f}" in body


def test_tier2_pipeline_falls_back_to_default_steel_on_none(
    tmp_path: Path,
) -> None:
    """Back-compat: omit material_id → DEFAULT_STEEL used, INP carries
    STEEL_S355 as the *MATERIAL block name."""
    case_dir = tmp_path / "phase19a-default-candidate"
    case_dir.mkdir()
    with pytest.raises(Tier2PipelineError):
        run_tier2_minimal_hex(
            case_dir,
            jobname="def",
            material_id=None,
            ccx_binary="/path/does/not/exist/ccx",
            timeout_sec=5.0,
        )
    body = (case_dir / "def.inp").read_text(encoding="utf-8")
    assert "*MATERIAL, NAME=STEEL_S355" in body


# ---------------------------------------------------------------------
# Pipeline-level refusal paths
# ---------------------------------------------------------------------


def test_pipeline_refuses_unknown_material_id(tmp_path: Path) -> None:
    case_dir = tmp_path / "phase19a-unknown-candidate"
    case_dir.mkdir()
    with pytest.raises(Tier2PipelineError) as excinfo:
        run_tier2_minimal_hex(
            case_dir,
            jobname="x",
            material_id="not-a-real-material",
            ccx_binary=LOCAL_CCX_BINARY,
            timeout_sec=5.0,
        )
    assert excinfo.value.stage == "resolve_material"


def test_pipeline_refuses_signed_registry_case(tmp_path: Path) -> None:
    """HF1.7a defense composes through the pipeline; the runner
    refuses signed-registry shapes."""
    case_dir = tmp_path / "GS-042"
    case_dir.mkdir()
    with pytest.raises(Tier2PipelineError) as excinfo:
        run_tier2_minimal_hex(
            case_dir,
            jobname="x",
            material_id="steel-s355",
            ccx_binary=LOCAL_CCX_BINARY,
            timeout_sec=5.0,
        )
    assert excinfo.value.stage == "run_ccx"
    assert "signed-registry" in str(excinfo.value).lower()


# ---------------------------------------------------------------------
# Tier2RunResult dataclass shape
# ---------------------------------------------------------------------


def test_tier2_run_result_is_frozen() -> None:
    """Defense against mutation during downstream rendering / audit."""
    from app.adapters.calculix import CalculiXRunResult

    fake = Tier2RunResult(
        material_resolved=DEFAULT_STEEL,
        material_reference="x",
        ccx_result=CalculiXRunResult(
            returncode=0,
            stdout_path=Path("/tmp/x.stdout.log"),
            stderr_path=Path("/tmp/x.stderr.log"),
            frd_path=Path("/tmp/x.frd"),
            dat_path=None,
            runtime_sec=0.5,
        ),
        inp_path=Path("/tmp/x.inp"),
    )
    with pytest.raises(Exception):
        fake.material_reference = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------
# T:-3 — load-bearing end-to-end pin (requires_solver opt-in)
# ---------------------------------------------------------------------


@pytest.mark.requires_solver
def test_aluminium_displaces_three_times_more_than_steel(
    tmp_path: Path,
) -> None:
    """The load-bearing physics pin. Steel E = 210 GPa, aluminium E =
    68.9 GPa, ratio ≈ 3.048. Under the same load + geometry + BCs,
    the elastic displacement scales as 1/E. So aluminium top-face
    displacement magnitude should be ~3× steel.

    Tolerance ±10% accounts for nodal extrapolation + integration
    artifacts on a single C3D8 element; the ratio is the load-bearing
    signal, not the absolute value.
    """
    from app.adapters.calculix import CalculiXReader
    from app.core.types import CanonicalField, UnitSystem

    # Steel run
    steel_dir = tmp_path / "phase19a-steel-candidate"
    steel_dir.mkdir()
    steel_result = run_tier2_minimal_hex(
        steel_dir,
        jobname="steel",
        material_id="steel-s355",
        ccx_binary=LOCAL_CCX_BINARY,
        timeout_sec=30.0,
    )
    assert steel_result.ccx_result.returncode == 0
    assert steel_result.ccx_result.frd_path is not None
    steel_reader = CalculiXReader(
        steel_result.ccx_result.frd_path, unit_system=UnitSystem.SI
    )
    steel_disp = steel_reader.get_field(
        CanonicalField.DISPLACEMENT, step_id=1
    )
    assert steel_disp is not None
    steel_uz_max = float(abs(steel_disp.at_nodes()[:, 2]).max())

    # Aluminium run
    al_dir = tmp_path / "phase19a-aluminium-candidate"
    al_dir.mkdir()
    al_result = run_tier2_minimal_hex(
        al_dir,
        jobname="al",
        material_id="aluminium-6061-t6",
        ccx_binary=LOCAL_CCX_BINARY,
        timeout_sec=30.0,
    )
    assert al_result.ccx_result.returncode == 0
    al_reader = CalculiXReader(
        al_result.ccx_result.frd_path, unit_system=UnitSystem.SI
    )
    al_disp = al_reader.get_field(CanonicalField.DISPLACEMENT, step_id=1)
    assert al_disp is not None
    al_uz_max = float(abs(al_disp.at_nodes()[:, 2]).max())

    # The load-bearing assertion: aluminium displaces more under same load.
    assert al_uz_max > steel_uz_max, (
        f"aluminium should displace more than steel under same load; "
        f"got steel={steel_uz_max:.3e} m, aluminium={al_uz_max:.3e} m"
    )
    # And the ratio should be approximately E_steel / E_al ≈ 3.048.
    ratio = al_uz_max / steel_uz_max
    expected_ratio = 210e9 / 68.9e9  # ≈ 3.048
    rel_err = abs(ratio - expected_ratio) / expected_ratio
    assert rel_err < 0.10, (
        f"displacement ratio aluminium/steel = {ratio:.3f}; "
        f"expected ≈ {expected_ratio:.3f} (E_steel/E_al); "
        f"relative error = {rel_err * 100:.1f}% (cap 10%)"
    )


@pytest.mark.requires_solver
def test_audit_trail_carries_resolved_material_citation(
    tmp_path: Path,
) -> None:
    """C:-1 — the run result carries the citation reference so the
    reviewer can audit which material was actually substituted into
    the INP, byte-identical to the library entry."""
    case_dir = tmp_path / "phase19a-audit-candidate"
    case_dir.mkdir()
    result = run_tier2_minimal_hex(
        case_dir,
        jobname="audit",
        material_id="aluminium-6061-t6",
        ccx_binary=LOCAL_CCX_BINARY,
        timeout_sec=30.0,
    )
    assert result.material_reference == get_material(
        "aluminium-6061-t6"
    ).reference
    assert "MMPDS-2023" in result.material_reference
