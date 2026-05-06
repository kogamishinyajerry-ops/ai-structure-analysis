"""Tests for scripts/check_commit_trailers.py (FF-07 / HF5)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


@pytest.fixture(scope="module")
def mod():
    import check_commit_trailers  # type: ignore[import-not-found]

    return check_commit_trailers


VALID_MESSAGE = """feat(ENG-16): enforce HF5 trailers

Execution-by: codex-primary
Reviewed-by: claude-opus47 APPROVE reports/codex_tool_reports/ff07_claude_audit.md
Linear-Issue: ENG-16
Codex-verified: FF-07-HF5@deadbeef
"""


def test_valid_message_passes_with_all_required_trailers(mod) -> None:
    assert (
        mod.validate_message(
            VALID_MESSAGE,
            require_reviewed_by=True,
            require_codex_verified=True,
        )
        == []
    )


def test_execution_by_must_be_codex_primary(mod) -> None:
    message = VALID_MESSAGE.replace("Execution-by: codex-primary", "Execution-by: claude-opus47")
    errors = mod.validate_message(message)
    assert any("Execution-by must be exactly codex-primary" in error for error in errors)


def test_linear_issue_must_match_eng_id(mod) -> None:
    message = VALID_MESSAGE.replace("Linear-Issue: ENG-16", "Linear-Issue: JIRA-16")
    errors = mod.validate_message(message)
    assert any("Linear-Issue must match ENG-<id>" in error for error in errors)


def test_reviewed_by_required_when_gate_active(mod) -> None:
    message = VALID_MESSAGE.replace(
        "Reviewed-by: claude-opus47 APPROVE reports/codex_tool_reports/ff07_claude_audit.md\n",
        "",
    )
    errors = mod.validate_message(message, require_reviewed_by=True)
    assert any("missing required trailer Reviewed-by" in error for error in errors)


def test_reviewed_by_must_be_approve_with_proof(mod) -> None:
    message = VALID_MESSAGE.replace(
        "Reviewed-by: claude-opus47 APPROVE reports/codex_tool_reports/ff07_claude_audit.md",
        "Reviewed-by: claude-opus47 CHANGES_REQUIRED reports/codex_tool_reports/ff07.md",
    )
    errors = mod.validate_message(message, require_reviewed_by=True)
    assert any("Reviewed-by must match" in error for error in errors)


def test_reviewed_by_rejects_template_placeholder(mod) -> None:
    message = VALID_MESSAGE.replace(
        "Reviewed-by: claude-opus47 APPROVE reports/codex_tool_reports/ff07_claude_audit.md",
        "Reviewed-by: claude-opus47 APPROVE <verdict-or-proof-ref>",
    )
    errors = mod.validate_message(message, require_reviewed_by=True)
    assert any("placeholder tokens" in error for error in errors)


def test_reviewed_by_rejects_embedded_pending_token(mod) -> None:
    message = VALID_MESSAGE.replace(
        "Reviewed-by: claude-opus47 APPROVE reports/codex_tool_reports/ff07_claude_audit.md",
        "Reviewed-by: claude-opus47 APPROVE pending",
    )
    errors = mod.validate_message(message, require_reviewed_by=True)
    assert any("placeholder tokens" in error for error in errors)


def test_codex_verified_optional_but_format_checked_when_present(mod) -> None:
    message = VALID_MESSAGE.replace("Codex-verified: FF-07-HF5@deadbeef", "Codex-verified: bad")
    errors = mod.validate_message(message)
    assert any("Codex-verified must match" in error for error in errors)


def test_codex_verified_can_be_required(mod) -> None:
    message = VALID_MESSAGE.replace("Codex-verified: FF-07-HF5@deadbeef\n", "")
    errors = mod.validate_message(message, require_codex_verified=True)
    assert any("missing required trailer Codex-verified" in error for error in errors)


def test_placeholders_are_rejected(mod) -> None:
    message = VALID_MESSAGE.replace("Codex-verified: FF-07-HF5@deadbeef", "Codex-verified: HEAD")
    errors = mod.validate_message(message, require_codex_verified=True)
    assert any("placeholder value for trailer Codex-verified" in error for error in errors)


def test_duplicate_trailers_are_rejected(mod) -> None:
    message = VALID_MESSAGE + "Linear-Issue: ENG-17\n"
    errors = mod.validate_message(message)
    assert any("duplicate trailer Linear-Issue" in error for error in errors)


def test_body_text_cannot_spoof_real_trailers(mod) -> None:
    message = """feat: body-only spoof

This prose mentions a fake trailer:

Execution-by: codex-primary
Linear-Issue: ENG-16

Then the body continues, so no final trailer block exists.
"""
    errors = mod.validate_message(message)
    assert any("missing required trailer Execution-by" in error for error in errors)
    assert any("missing required trailer Linear-Issue" in error for error in errors)


def test_message_file_cli_reports_failures(mod, tmp_path: Path, capsys) -> None:
    message_file = tmp_path / "COMMIT_EDITMSG"
    message_file.write_text("bad commit\n", encoding="utf-8")
    rc = mod.main(["--message-file", str(message_file)])
    assert rc == 1
    assert "HF5 commit-trailer violation" in capsys.readouterr().err


def test_range_cli_checks_temp_repo(mod, tmp_path: Path, monkeypatch, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    subprocess.run(["git", "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "config", "user.name", "test"], check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], check=True)

    (repo / "base.txt").write_text("base", encoding="utf-8")
    subprocess.run(["git", "add", "base.txt"], check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], check=True)
    base_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()

    (repo / "good.txt").write_text("good", encoding="utf-8")
    subprocess.run(["git", "add", "good.txt"], check=True)
    subprocess.run(["git", "commit", "-q", "-m", VALID_MESSAGE], check=True)

    rc = mod.main(
        [
            "--range",
            f"{base_sha}..HEAD",
            "--require-reviewed-by",
            "--require-codex-verified",
        ]
    )
    assert rc == 0
    assert "HF5 commit-trailer check passed" in capsys.readouterr().out
