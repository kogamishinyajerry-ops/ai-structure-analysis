"""Regression guard for the cross_check_phase21a --workdir option (Codex R2 P1).

The runners' own HF1.7a refusal only fires when ``case_dir.name`` itself
matches ``^GS-\\d{3}$`` — so a persistent ``--workdir`` pointed under a
``golden_samples/`` tree (signed OR candidate) would bypass the signed-registry
read-only guarantee and scatter scratch ``.msh/.inp/.frd`` solver artifacts
into evidence directories.  ``_case_workspace`` must therefore refuse,
fail-closed, BEFORE creating anything; this test runs in the required
``lint-and-test`` job so the guard cannot regress silently.
"""

from __future__ import annotations

import contextlib
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "cross_check_phase21a", REPO_ROOT / "scripts" / "cross_check_phase21a.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def xc():
    return _load_module()


@pytest.mark.parametrize(
    "rel",
    [
        "golden_samples",
        "golden_samples/GS-001",
        "golden_samples/GS-001/scratch",
        "golden_samples/nafems-le10-thick-plate-candidate",
        "golden_samples/nafems-le10-thick-plate-candidate/data/run_scratch",
    ],
    ids=["root", "signed", "signed-subdir", "candidate", "candidate-subdir"],
)
def test_workdir_refused_inside_golden_samples(xc, rel: str) -> None:
    """Any workdir at/under golden_samples is refused before mkdir."""
    target = REPO_ROOT / rel
    existed_before = target.exists()
    with pytest.raises(SystemExit) as exc, contextlib.ExitStack() as stack:
        xc._case_workspace(stack, target, "guard-test-")
    assert exc.value.code == 2
    # fail-closed means REFUSE-without-touching: nothing got created.
    assert target.exists() == existed_before


def test_workdir_refused_via_indirect_path(xc, tmp_path: Path) -> None:
    """Path tricks (../ traversal back into golden_samples) are resolved first."""
    sneaky = REPO_ROOT / "tmp" / ".." / "golden_samples" / "GS-001" / "ws"
    with pytest.raises(SystemExit), contextlib.ExitStack() as stack:
        xc._case_workspace(stack, sneaky, "guard-test-")
    assert not (REPO_ROOT / "golden_samples" / "GS-001" / "ws").exists()


def test_workdir_persists_outside_golden_samples(xc, tmp_path: Path) -> None:
    wd = tmp_path / "phase21a-ws"
    with contextlib.ExitStack() as stack:
        base = xc._case_workspace(stack, wd, "guard-test-")
        (base / "artifact.txt").write_text("x")
    assert wd.is_dir() and (wd / "artifact.txt").is_file(), (
        "persistent workdir artifacts must survive the stack"
    )


def test_default_tempdir_still_deleted(xc) -> None:
    """No --workdir → the historical TemporaryDirectory flow, deleted on exit."""
    with contextlib.ExitStack() as stack:
        base = xc._case_workspace(stack, None, "guard-test-")
        probe = base
        assert base.is_dir()
    assert not probe.exists(), "default tempdir must be cleaned up on stack exit"


def test_module_main_wires_workdir_flag(xc) -> None:
    """The CLI surface actually exposes --workdir (wiring, not just the helper)."""
    import argparse

    # main() builds its parser internally; assert the flag parses.
    monkey_argv = ["prog", "--skip", "cantilever", "--skip", "plate", "--workdir", "tmp/x"]
    old = sys.argv
    try:
        sys.argv = monkey_argv
        # both runners skipped -> main returns 0 without solving anything
        assert xc.main() == 0
    except argparse.ArgumentError:  # pragma: no cover - explicit failure signal
        pytest.fail("--workdir flag not wired into the CLI")
    finally:
        sys.argv = old
