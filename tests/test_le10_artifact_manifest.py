"""Seal check for the LE10 artifact manifest (ADR-027 G-2 packet item 5).

``golden_samples/nafems-le10-thick-plate-candidate/artifact_manifest.json``
pins the SHA-256 of every committed evidence file for the NAFEMS LE10
candidate.  This test re-hashes the sealed set on every PR (root ``tests/``
runs in the required ``lint-and-test`` job), so any byte change to sealed
evidence is a loud, reviewable event instead of a silent drift.

Honesty boundary: a green seal means the committed evidence is byte-stable.
It is NOT signed validation — item 6 (reproduce-CLI audit log, V2-2) is now
CLOSED (scripts/reproduce_case.py), but the manifest still records G-2 item 7
(owner-authorized independent signoff) as OPEN.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CASE = REPO_ROOT / "golden_samples" / "nafems-le10-thick-plate-candidate"
MANIFEST = CASE / "artifact_manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def test_manifest_exists_and_declares_open_items() -> None:
    m = _manifest()
    assert m["case_id"] == "nafems-le10-thick-plate-candidate"
    # The honesty banner is load-bearing: the packet must keep declaring what
    # it does NOT yet have, until those items genuinely close.
    coverage = m["g2_packet_coverage"]
    # Item 6 closed by ADR-027 V2-2 (scripts/reproduce_case.py); the packet must
    # name the closing mechanism, not silently flip to "covered".
    assert coverage["6_reproduce_cli_audit_log"].startswith("CLOSED")
    assert "reproduce_case.py" in coverage["6_reproduce_cli_audit_log"]
    # Item 7 (independent signoff) genuinely remains open — no AI self-sign.
    assert coverage["7_independent_review_signoff"].startswith("OPEN")
    assert "NOT signed validation" in m["claim_tier"]


def test_sealed_artifacts_hashes_match() -> None:
    m = _manifest()
    sealed = m["sealed_artifacts"]
    assert len(sealed) >= 6, "sealed set unexpectedly shrank"
    mismatches = []
    for rel, meta in sealed.items():
        p = CASE / rel
        if not p.is_file():
            mismatches.append(f"{rel}: file missing")
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest != meta["sha256"]:
            mismatches.append(f"{rel}: sha256 {digest[:12]}… != sealed {meta['sha256'][:12]}…")
        if p.stat().st_size != meta["bytes"]:
            mismatches.append(f"{rel}: size {p.stat().st_size} != sealed {meta['bytes']}")
    assert not mismatches, (
        "sealed LE10 evidence drifted — if intentional, regenerate the manifest "
        "in the same reviewed change: " + "; ".join(mismatches)
    )


def test_sealed_set_covers_all_tracked_case_files() -> None:
    """Every git-tracked file in the candidate dir is either sealed or the
    manifest itself — no unsealed evidence can ride along silently.  Untracked
    local solver outputs are policy-excluded (see the manifest note)."""
    import subprocess

    m = _manifest()
    sealed = set(m["sealed_artifacts"])
    case_rel = CASE.relative_to(REPO_ROOT)
    ls = subprocess.run(
        ["git", "ls-files", str(case_rel)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    git_tracked = {
        str(Path(line).relative_to(case_rel)) for line in ls.stdout.splitlines() if line.strip()
    }
    unsealed = git_tracked - sealed - {"artifact_manifest.json"}
    assert not unsealed, f"tracked evidence files missing from the seal: {sorted(unsealed)}"
