"""Tests for ``report-cli --doctor`` — RFC-001 W5c install probe.

The probe is the engineer's first move when the Electron shell can't
spawn ``report-cli``. It must:

* run without ``--frd`` / ``--kind``
* print a self-diagnostic to stdout (so the Electron renderer's stdout
  pane shows it without users hunting through stderr)
* exit 0 when the install is healthy
* exit 3 when a required dep is missing or unimportable (matches the
  domain-refusal exit-code class in the cli.py contract)
"""

from __future__ import annotations

import sys

import pytest
from app.services.report.cli import build_parser, main


def test_parser_accepts_doctor_alone() -> None:
    """`--doctor` must parse cleanly without --frd/--kind."""
    parser = build_parser()
    ns = parser.parse_args(["--doctor"])
    assert ns.doctor is True
    assert ns.frd is None
    assert ns.kind is None


def test_doctor_default_off() -> None:
    """`--doctor` defaults to off so existing report runs aren't
    surprised by a flag they didn't pass."""
    parser = build_parser()
    ns = parser.parse_args(["--frd", "x.frd", "--kind", "static"])
    assert ns.doctor is False


def test_doctor_runs_returns_zero_in_healthy_env(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """In the dev / CI environment numpy + python-docx + the in-tree
    modules are all importable, so doctor must exit 0."""
    rc = main(["--doctor"])
    assert rc == 0

    captured = capsys.readouterr()
    # Spot-check that the diagnostic actually printed something useful.
    assert "report-cli --doctor" in captured.out
    assert "python:" in captured.out
    assert "numpy:" in captured.out
    assert "python-docx:" in captured.out
    # Healthy summary line is on stdout, not stderr.
    assert "all required components are healthy" in captured.out


def test_doctor_reports_missing_hard_dep(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When a hard dep is missing, doctor must exit 3 and print a
    'NOT INSTALLED' line for it on stdout (so the engineer sees what
    to install). The summary failure line goes to stderr.

    Setting ``sys.modules["docx"] = None`` is the documented way to
    make ``import docx`` raise ImportError without touching disk:
    importlib treats a None entry in the cache as a sentinel meaning
    'known not to exist'. That probes the doctor's own try/except
    handling without taking the python-docx wheel offline.
    """
    monkeypatch.setitem(sys.modules, "docx", None)

    rc = main(["--doctor"])
    assert rc == 3

    captured = capsys.readouterr()
    assert "python-docx: NOT INSTALLED" in captured.out
    assert "missing or broken" in captured.err


def test_main_without_frd_or_doctor_exits_two(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Removing argparse-required from --frd shifts the check to main();
    must still exit 2 with a clear hint about --doctor."""
    with pytest.raises(SystemExit) as excinfo:
        main(["--kind", "static"])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "--frd" in err
    assert "--doctor" in err


def test_main_without_kind_or_doctor_exits_two(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Same as above, for --kind."""
    with pytest.raises(SystemExit) as excinfo:
        main(["--frd", "x.frd"])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "--kind" in err
    assert "--doctor" in err


def test_doctor_exit_path_uses_sys_executable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The python interpreter line must surface the actual interpreter
    path, not a generic 'python' string. Engineers debugging an
    'install looks fine but Electron can't find it' situation need to
    see which venv the report-cli is running under."""
    rc = main(["--doctor"])
    assert rc == 0
    captured = capsys.readouterr()
    assert sys.executable in captured.out


def test_doctor_reports_broken_hard_dep_not_just_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex R1 MEDIUM: a half-installed numpy / python-docx that
    raises a non-ImportError on import (RuntimeError, AttributeError,
    transitive ABI mismatch, etc.) must not crash the doctor — the
    contract says 'missing or unimportable'. Verify the BROKEN branch
    surfaces and exits 3.
    """
    import importlib

    real_import_module = importlib.import_module

    def fake_import_module(name: str, *args: object, **kwargs: object) -> object:
        if name == "docx":
            raise RuntimeError("simulated: shared C ext aborted on load")
        return real_import_module(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    rc = main(["--doctor"])
    assert rc == 3

    captured = capsys.readouterr()
    assert "python-docx: BROKEN" in captured.out
    assert "RuntimeError" in captured.out
    # numpy still ran (probe order: numpy first, then docx) and
    # downstream in-tree probes still ran — broken deps don't short-
    # circuit the diagnostic.
    assert "numpy:" in captured.out
    assert "missing or broken" in captured.err


def test_report_run_emits_progress_stages_to_stderr(
    tmp_path: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W5e: a successful report run must emit per-stage progress lines
    on stderr so the Electron wedge can render an audit-trail. stdout
    stays single-line ('wrote ...') so callers piping report-cli into
    another tool keep their existing contract.

    Uses GS-001 .frd. Skips if the fixture is missing — the project
    should never ship without it but unit tests must not crash if a
    contributor builds in a partial checkout.
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    frd = repo_root / "golden_samples" / "GS-001" / "gs001_result.frd"
    if not frd.is_file():
        pytest.skip(f"GS-001 fixture missing at {frd}")

    out = tmp_path / "report.docx"  # type: ignore[attr-defined]
    rc = main(
        [
            "--frd",
            str(frd),
            "--kind",
            "static",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()

    # All 4 stage headers must appear, in order, on stderr.
    expected_prefixes = [
        "[1/4] reading CalculiX .frd:",
        "[2/4] producing report:",
        "[3/4] validating template:",
        "[4/4] exporting DOCX:",
    ]
    pos = 0
    for prefix in expected_prefixes:
        idx = captured.err.find(prefix, pos)
        assert idx >= 0, (
            f"missing or out-of-order stderr line {prefix!r}; full stderr:\n{captured.err}"
        )
        pos = idx + len(prefix)

    # Detail lines must follow stages 1 and 2.
    assert "      → opened (unit_system=si-mm)" in captured.err
    assert "      → 2 evidence items, template=equipment_foundation_static" in captured.err

    # stdout still single-line summary — engineers script around this.
    stdout_lines = [ln for ln in captured.out.splitlines() if ln.strip()]
    assert len(stdout_lines) == 1
    assert stdout_lines[0].startswith("wrote ")


def test_no_validate_template_drops_validation_stage(
    tmp_path: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With --no-validate-template, total_stages drops to 3 and the
    validation stage line must not appear. The [N/T] denominator
    must update accordingly."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    frd = repo_root / "golden_samples" / "GS-001" / "gs001_result.frd"
    if not frd.is_file():
        pytest.skip(f"GS-001 fixture missing at {frd}")

    out = tmp_path / "report.docx"  # type: ignore[attr-defined]
    rc = main(
        [
            "--frd",
            str(frd),
            "--kind",
            "static",
            "--output",
            str(out),
            "--no-validate-template",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()

    assert "[1/3]" in captured.err
    assert "[2/3]" in captured.err
    assert "[3/3] exporting DOCX:" in captured.err
    assert "[4/" not in captured.err  # no fourth stage in this mode
    assert "validating template:" not in captured.err


def test_cli_module_loads_when_inhouse_submodule_is_broken(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex R1 HIGH + R2 NIT: ``import app.services.report.cli`` must
    NOT fail at module load when an in-tree submodule it used to import
    at the top is broken — otherwise --doctor never gets a chance to
    diagnose the broken submodule. AND, the doctor invoked against
    that broken state must produce the contracted IMPORT FAILED line
    and exit 3 (not silently succeed, not crash).

    Probe by deleting cached cli + adapter, poisoning the adapter's
    sys.modules entry, re-importing cli, then calling main(['--doctor']).
    """
    import importlib

    # Wipe any cached state so the re-import goes through the real
    # import machinery (which will hit our poisoned cache entry).
    monkeypatch.delitem(sys.modules, "app.services.report.cli", raising=False)
    monkeypatch.delitem(sys.modules, "app.adapters.calculix", raising=False)
    # ``None`` in sys.modules is the documented sentinel for "module
    # known not to exist" — any import of this name now raises
    # ImportError without disk access.
    monkeypatch.setitem(sys.modules, "app.adapters.calculix", None)

    # The whole point: this re-import must NOT raise. Under the old
    # eager-import scheme (W5c initial), it raised ImportError because
    # cli.py's top-of-file `from app.adapters.calculix import ...` ran
    # before the doctor branch.
    cli_module = importlib.import_module("app.services.report.cli")
    assert hasattr(cli_module, "main")

    # Codex R2 NIT: re-importability is necessary but not sufficient.
    # Assert the user-visible contract too.
    rc = cli_module.main(["--doctor"])
    assert rc == 3
    captured = capsys.readouterr()
    assert "app.adapters.calculix: IMPORT FAILED" in captured.out
