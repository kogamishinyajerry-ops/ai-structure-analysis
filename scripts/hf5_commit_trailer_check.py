#!/usr/bin/env python3
"""HF5 commit-trailer checker for AI-Structure-FEA.

Validates the audit trailers required by the Codex-solo Linear workflow:

  Execution-by: codex-gpt-5.4-xhigh
  Self-verified: <CLAIM-ID>@<sha> (fresh-subtask <subtask-id>)
  Linear-issue: ENG-<n>
  Linear-decision: <ENG-* / ADR-* / DEC-*>  # optional

Two invocation modes are supported:

1. ``--message-file <path>`` for a local ``commit-msg`` hook.
2. ``--from-ref <ref>`` for a local PR-range check, e.g.
   ``python scripts/hf5_commit_trailer_check.py --from-ref origin/main``.

The checker intentionally validates commit messages only. It does not
decide whether a Linear issue may advance through Pending Review.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

TRAILER_KEYS = (
    "Execution-by",
    "Self-verified",
    "Linear-issue",
    "Linear-decision",
)
REQUIRED_TRAILERS = ("Execution-by", "Self-verified", "Linear-issue")
PLACEHOLDER_VALUES = {
    "",
    "n/a",
    "na",
    "none",
    "pending",
    "pending-fresh-subtask",
    "tbd",
    "todo",
}

SELF_VERIFIED_RE = re.compile(
    r"^[A-Z0-9][A-Z0-9._-]*@[0-9a-f]{7,40} "
    r"\(fresh-subtask [A-Za-z0-9._:-]+\)$"
)
LINEAR_ISSUE_RE = re.compile(r"^ENG-[0-9]+$")
LINEAR_DECISION_RE = re.compile(r"^(ENG-[0-9]+|ADR-[A-Z0-9._-]+|DEC-[A-Z0-9._-]+)$")
TRAILER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.*)$")


@dataclass(frozen=True)
class CommitMessage:
    source: str
    body: str


def parse_relevant_trailers(message: str) -> dict[str, list[str]]:
    """Return relevant trailer values by key.

    Git trailers conventionally live at the end of the commit message,
    but this parser scans the whole message for the specific HF5 keys
    so a malformed duplicate cannot hide above the final trailer block.
    """
    trailers: dict[str, list[str]] = {key: [] for key in TRAILER_KEYS}
    for line in message.splitlines():
        match = TRAILER_RE.match(line.strip())
        if not match:
            continue
        key, value = match.groups()
        if key in trailers:
            trailers[key].append(value.strip())
    return trailers


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in PLACEHOLDER_VALUES


def validate_message(message: str, *, source: str = "<message>") -> list[str]:
    """Return validation errors for one commit message."""
    errors: list[str] = []
    trailers = parse_relevant_trailers(message)

    for key in REQUIRED_TRAILERS:
        values = trailers[key]
        if not values:
            errors.append(f"{source}: missing required trailer {key}")
            continue
        if len(values) > 1:
            errors.append(f"{source}: duplicate trailer {key}")
            continue
        if _is_placeholder(values[0]):
            errors.append(f"{source}: placeholder value for trailer {key}")

    execution = trailers["Execution-by"]
    if (
        len(execution) == 1
        and not _is_placeholder(execution[0])
        and not execution[0].startswith("codex-gpt-")
    ):
        errors.append(f"{source}: Execution-by must name the Codex execution model")

    self_verified = trailers["Self-verified"]
    if (
        len(self_verified) == 1
        and not _is_placeholder(self_verified[0])
        and not SELF_VERIFIED_RE.match(self_verified[0])
    ):
        errors.append(f"{source}: Self-verified must match '<CLAIM-ID>@<sha> (fresh-subtask <id>)'")

    linear_issue = trailers["Linear-issue"]
    if (
        len(linear_issue) == 1
        and not _is_placeholder(linear_issue[0])
        and not LINEAR_ISSUE_RE.match(linear_issue[0])
    ):
        errors.append(f"{source}: Linear-issue must match ENG-<n>")

    linear_decision = trailers["Linear-decision"]
    if len(linear_decision) > 1:
        errors.append(f"{source}: duplicate trailer Linear-decision")
    elif len(linear_decision) == 1:
        value = linear_decision[0]
        if _is_placeholder(value):
            errors.append(f"{source}: placeholder value for trailer Linear-decision")
        elif not LINEAR_DECISION_RE.match(value):
            errors.append(f"{source}: Linear-decision must match ENG-<n>, ADR-*, or DEC-*")

    return errors


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"`git {' '.join(args)}` failed rc={result.returncode}: {result.stderr.strip()}"
        )
    return result.stdout


def commit_messages_from_ref(ref: str) -> list[CommitMessage]:
    """Return commit messages for commits in ``merge-base(ref, HEAD)..HEAD``."""
    merge_base = _git(["merge-base", ref, "HEAD"]).strip()
    revs = [
        line
        for line in _git(["rev-list", "--reverse", f"{merge_base}..HEAD"]).splitlines()
        if line.strip()
    ]
    return [
        CommitMessage(source=rev[:12], body=_git(["log", "-1", "--format=%B", rev])) for rev in revs
    ]


def check_messages(messages: list[CommitMessage]) -> list[str]:
    errors: list[str] = []
    for message in messages:
        errors.extend(validate_message(message.body, source=message.source))
    return errors


def report(errors: list[str]) -> int:
    if not errors:
        return 0
    sys.stderr.write("HF5 commit-trailer violation.\n\n")
    for error in errors:
        sys.stderr.write(f"  - {error}\n")
    sys.stderr.write(
        "\nRequired trailers:\n"
        "  Execution-by: codex-gpt-5.4-xhigh\n"
        "  Self-verified: <CLAIM-ID>@<sha> (fresh-subtask <id>)\n"
        "  Linear-issue: ENG-<n>\n"
        "  Linear-decision: <ENG-* / ADR-* / DEC-*>  # optional\n"
    )
    return 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="HF5 commit trailer checker (Codex Linear workflow)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--message-file",
        type=Path,
        help="Validate one commit message file (commit-msg hook mode).",
    )
    group.add_argument(
        "--from-ref",
        metavar="REF",
        help="Validate commits in merge-base(REF, HEAD)..HEAD.",
    )
    args = parser.parse_args(argv[1:])

    try:
        if args.message_file is not None:
            errors = validate_message(
                args.message_file.read_text(encoding="utf-8"),
                source=str(args.message_file),
            )
        else:
            errors = check_messages(commit_messages_from_ref(args.from_ref))
    except (OSError, RuntimeError) as exc:
        sys.stderr.write(f"HF5 commit-trailer checker failed: {exc}\n")
        return 2

    return report(errors)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
