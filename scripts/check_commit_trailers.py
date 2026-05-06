#!/usr/bin/env python3
"""Validate HF5 audit trailers on commit messages.

FF-07 turns ADR-011's commit-trailer convention into a mechanical check.
The parser deliberately delegates trailer-block detection to
``git interpret-trailers --parse`` so prose in the commit body cannot spoof
real trailers.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

REQUIRED_BASE_TRAILERS = ("Execution-by", "Linear-Issue")
PLACEHOLDER_VALUES = {
    "",
    "<claim-id>",
    "<id>",
    "<pending>",
    "<proof-ref>",
    "<sha>",
    "<verdict>",
    "<verdict-or-proof-ref>",
    "head",
    "n/a",
    "na",
    "none",
    "pending",
    "tbd",
    "todo",
}

CLAIM_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*@[0-9a-fA-F]{7,40}$")
LINEAR_ISSUE_RE = re.compile(r"^ENG-[1-9][0-9]*$")
REVIEWED_BY_RE = re.compile(r"^claude-opus47\s+APPROVE\s+\S.+$")


@dataclass(frozen=True)
class CommitMessage:
    source: str
    body: str


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in PLACEHOLDER_VALUES


def _contains_placeholder_token(value: str) -> bool:
    lowered = value.strip().lower()
    if "<" in lowered or ">" in lowered:
        return True
    return any(token in lowered.split() for token in {"pending", "tbd", "todo"})


def _run_git(args: list[str], *, input_text: str | None = None, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        input=input_text,
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"`git {' '.join(args)}` failed rc={result.returncode}: {result.stderr.strip()}"
        )
    return result.stdout


def parse_trailers(message: str) -> dict[str, list[str]]:
    """Return final trailer-block values by canonical trailer key."""
    parsed = _run_git(["interpret-trailers", "--parse"], input_text=message)
    trailers: dict[str, list[str]] = {}
    for line in parsed.splitlines():
        if ":" not in line:
            continue
        raw_key, raw_value = line.split(":", 1)
        key = raw_key.strip()
        value = raw_value.strip()
        trailers.setdefault(key.lower(), []).append(value)
    return trailers


def _values(trailers: dict[str, list[str]], key: str) -> list[str]:
    return trailers.get(key.lower(), [])


def _require_single_value(
    errors: list[str], trailers: dict[str, list[str]], key: str, *, source: str
) -> str | None:
    values = _values(trailers, key)
    if not values:
        errors.append(f"{source}: missing required trailer {key}")
        return None
    if len(values) > 1:
        errors.append(f"{source}: duplicate trailer {key}")
        return None
    value = values[0]
    if _is_placeholder(value):
        errors.append(f"{source}: placeholder value for trailer {key}")
        return None
    return value


def validate_message(
    message: str,
    *,
    source: str = "<message>",
    require_reviewed_by: bool = False,
    require_codex_verified: bool = False,
) -> list[str]:
    """Return validation errors for one commit message."""
    errors: list[str] = []
    trailers = parse_trailers(message)

    execution_by = _require_single_value(errors, trailers, "Execution-by", source=source)
    if execution_by is not None and execution_by != "codex-primary":
        errors.append(f"{source}: Execution-by must be exactly codex-primary")

    linear_issue = _require_single_value(errors, trailers, "Linear-Issue", source=source)
    if linear_issue is not None and not LINEAR_ISSUE_RE.match(linear_issue):
        errors.append(f"{source}: Linear-Issue must match ENG-<id>")

    if require_reviewed_by:
        reviewed_by = _require_single_value(errors, trailers, "Reviewed-by", source=source)
        if reviewed_by is not None and not REVIEWED_BY_RE.match(reviewed_by):
            errors.append(f"{source}: Reviewed-by must match 'claude-opus47 APPROVE <proof-ref>'")
        elif reviewed_by is not None and _contains_placeholder_token(reviewed_by):
            errors.append(f"{source}: Reviewed-by must not contain placeholder tokens")

    if require_codex_verified:
        codex_verified = _require_single_value(errors, trailers, "Codex-verified", source=source)
        if codex_verified is not None and not CLAIM_REF_RE.match(codex_verified):
            errors.append(f"{source}: Codex-verified must match <claim-id>@<7-40 hex sha>")
    else:
        values = _values(trailers, "Codex-verified")
        if len(values) > 1:
            errors.append(f"{source}: duplicate trailer Codex-verified")
        elif len(values) == 1:
            value = values[0]
            if _is_placeholder(value):
                errors.append(f"{source}: placeholder value for trailer Codex-verified")
            elif not CLAIM_REF_RE.match(value):
                errors.append(f"{source}: Codex-verified must match <claim-id>@<7-40 hex sha>")

    return errors


def commit_messages_from_range(ref_range: str, *, cwd: Path | None = None) -> list[CommitMessage]:
    """Return commit messages in chronological order for ``ref_range``."""
    revs = [
        line
        for line in _run_git(["rev-list", "--reverse", ref_range], cwd=cwd).splitlines()
        if line.strip()
    ]
    messages: list[CommitMessage] = []
    for rev in revs:
        body = _run_git(["log", "-1", "--format=%B", rev], cwd=cwd)
        subject = body.splitlines()[0] if body.splitlines() else "<empty subject>"
        messages.append(CommitMessage(source=f"{rev[:12]} {subject}", body=body))
    return messages


def commit_messages_from_ref(ref: str, *, cwd: Path | None = None) -> list[CommitMessage]:
    merge_base = _run_git(["merge-base", ref, "HEAD"], cwd=cwd).strip()
    return commit_messages_from_range(f"{merge_base}..HEAD", cwd=cwd)


def check_messages(
    messages: Iterable[CommitMessage],
    *,
    require_reviewed_by: bool = False,
    require_codex_verified: bool = False,
) -> list[str]:
    errors: list[str] = []
    for message in messages:
        errors.extend(
            validate_message(
                message.body,
                source=message.source,
                require_reviewed_by=require_reviewed_by,
                require_codex_verified=require_codex_verified,
            )
        )
    return errors


def _report(errors: list[str]) -> int:
    if not errors:
        print("HF5 commit-trailer check passed")
        return 0
    sys.stderr.write("HF5 commit-trailer violation.\n\n")
    for error in errors:
        sys.stderr.write(f"  - {error}\n")
    sys.stderr.write(
        "\nRequired trailers:\n"
        "  Execution-by: codex-primary\n"
        "  Linear-Issue: ENG-<id>\n"
        "  Reviewed-by: claude-opus47 APPROVE <proof-ref>\n"
        "    # when review gate is active\n"
        "  Codex-verified: <claim-id>@<7-40 hex sha>\n"
        "    # when HF5 claim proof is required\n"
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    args_in = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Validate ADR-011 / FF-07 commit trailers.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--message-file", type=Path, help="Validate one commit message file.")
    group.add_argument(
        "--range", dest="ref_range", help="Validate commits in an explicit git range."
    )
    group.add_argument(
        "--from-ref",
        metavar="REF",
        help="Validate commits in merge-base(REF, HEAD)..HEAD.",
    )
    parser.add_argument(
        "--require-reviewed-by",
        action="store_true",
        help="Require Reviewed-by trailer for mandatory review gates.",
    )
    parser.add_argument(
        "--require-codex-verified",
        action="store_true",
        help="Require Codex-verified trailer and validate claim-id@sha format.",
    )
    parsed = parser.parse_args(args_in)

    try:
        if parsed.message_file is not None:
            messages = [
                CommitMessage(
                    source=str(parsed.message_file),
                    body=parsed.message_file.read_text(encoding="utf-8"),
                )
            ]
        elif parsed.ref_range:
            messages = commit_messages_from_range(parsed.ref_range)
        else:
            messages = commit_messages_from_ref(parsed.from_ref)
        errors = check_messages(
            messages,
            require_reviewed_by=parsed.require_reviewed_by,
            require_codex_verified=parsed.require_codex_verified,
        )
    except (OSError, RuntimeError) as exc:
        sys.stderr.write(f"HF5 commit-trailer checker failed: {exc}\n")
        return 2

    return _report(errors)


if __name__ == "__main__":
    raise SystemExit(main())
