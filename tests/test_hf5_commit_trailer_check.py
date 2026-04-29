"""Tests for scripts/hf5_commit_trailer_check.py (ENG-16 / HF5)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_checker():
    import hf5_commit_trailer_check as hf5  # type: ignore[import-not-found]

    return hf5


hf5 = _load_checker()


VALID_MESSAGE = """feat(ENG-16): enforce HF5 commit trailers

Execution-by: codex-gpt-5.4-xhigh
Self-verified: ENG16-HF5-2026-04-29@deadbeef (fresh-subtask 019dd8b5)
Linear-issue: ENG-16
"""


def test_valid_message_passes() -> None:
    assert hf5.validate_message(VALID_MESSAGE) == []


def test_valid_message_accepts_optional_linear_decision() -> None:
    msg = VALID_MESSAGE + "Linear-decision: ADR-GS101-SIGNED-OPENRADIOSS-CARVEOUT\n"
    assert hf5.validate_message(msg) == []


def test_missing_required_trailer_fails() -> None:
    msg = VALID_MESSAGE.replace("Execution-by: codex-gpt-5.4-xhigh\n", "")
    errors = hf5.validate_message(msg, source="abc123")
    assert "abc123: missing required trailer Execution-by" in errors


def test_placeholder_self_verified_fails() -> None:
    msg = VALID_MESSAGE.replace(
        "Self-verified: ENG16-HF5-2026-04-29@deadbeef (fresh-subtask 019dd8b5)",
        "Self-verified: pending-fresh-subtask",
    )
    errors = hf5.validate_message(msg)
    assert any("placeholder value for trailer Self-verified" in e for e in errors)


def test_malformed_self_verified_fails() -> None:
    msg = VALID_MESSAGE.replace(
        "Self-verified: ENG16-HF5-2026-04-29@deadbeef (fresh-subtask 019dd8b5)",
        "Self-verified: ENG16-HF5-2026-04-29 deadbeef",
    )
    errors = hf5.validate_message(msg)
    assert any("Self-verified must match" in e for e in errors)


def test_malformed_linear_issue_fails() -> None:
    msg = VALID_MESSAGE.replace("Linear-issue: ENG-16", "Linear-issue: AI-FEA-16")
    errors = hf5.validate_message(msg)
    assert any("Linear-issue must match ENG-<n>" in e for e in errors)


def test_duplicate_required_trailer_fails() -> None:
    msg = VALID_MESSAGE + "Linear-issue: ENG-17\n"
    errors = hf5.validate_message(msg)
    assert any("duplicate trailer Linear-issue" in e for e in errors)


def test_execution_by_must_name_codex_model() -> None:
    msg = VALID_MESSAGE.replace(
        "Execution-by: codex-gpt-5.4-xhigh",
        "Execution-by: claude-code-opus47",
    )
    errors = hf5.validate_message(msg)
    assert any("Execution-by must name the Codex execution model" in e for e in errors)


def test_malformed_linear_decision_fails() -> None:
    msg = VALID_MESSAGE + "Linear-decision: notion-page-123\n"
    errors = hf5.validate_message(msg)
    assert any("Linear-decision must match" in e for e in errors)


def test_message_file_cli_passes(tmp_path: Path) -> None:
    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_text(VALID_MESSAGE, encoding="utf-8")
    assert hf5.main(["hf5_commit_trailer_check.py", "--message-file", str(msg_file)]) == 0


def test_message_file_cli_reports_failures(tmp_path: Path, capsys) -> None:
    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_text("bad commit\n", encoding="utf-8")
    rc = hf5.main(["hf5_commit_trailer_check.py", "--message-file", str(msg_file)])
    assert rc == 1
    assert "HF5 commit-trailer violation" in capsys.readouterr().err


def test_check_messages_aggregates_by_source() -> None:
    messages = [
        hf5.CommitMessage(source="good", body=VALID_MESSAGE),
        hf5.CommitMessage(source="bad", body="bad commit\n"),
    ]
    errors = hf5.check_messages(messages)
    assert any(error.startswith("bad: missing required trailer") for error in errors)
