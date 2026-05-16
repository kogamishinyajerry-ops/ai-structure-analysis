"""Tier 1 candidate reproducibility manifest (FM-04a Phase 5 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Captures, for a single Tier 1 candidate case, the *environment* in which
its evidence was produced. A reviewer reading two snapshots taken weeks
apart can compare these manifests to decide whether a numerical
difference came from a fix, a regression, or simply a different
toolchain.

What this is NOT:
* This is NOT a Tier 2 byte-frozen registry of solver dependencies.
* This is NOT a substitute for the FM-04b P8 sealed packet, which
  bundles independent reviewer signoff + immutable hashes.
* The manifest does NOT execute the case. It only inspects the case's
  generator script (SHA-256) + the current python interpreter and
  pip-resolvable packages. No solver is invoked.

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``.
The builder asserts the rendered manifest stays clean against these
positive claims; ``not <claim>`` disclaimer forms remain allowed.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from ._schema_versions import REPRODUCIBILITY_MANIFEST_SCHEMA_VERSION
from .acceptance_packet import CLAIM_BOUNDARY

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate reproducibility manifest only; not signed "
    "validation; not benchmark agreement; not a Tier 2 byte-frozen "
    "dependency registry. The FM-04b P8 sealed packet remains gated "
    "by ADR-024 (full) + independent reviewer signoff."
)

# Packages whose versions are most likely to influence Tier 1 candidate
# numerical output. Kept narrow on purpose: a broad freeze of the full
# pip set is the FM-04b P8 sealed packet's job, not this manifest's.
_TRACKED_PACKAGES: tuple[str, ...] = (
    "fastapi",
    "starlette",
    "httpx",
    "pydantic",
    "numpy",
    "pyvista",
    "python-docx",
    "pillow",
    "matplotlib",
)


@dataclass(frozen=True)
class ScriptFingerprint:
    """Per-file SHA-256 of a Tier 1 candidate generator / orchestrator script."""

    relpath: str
    sha256: str
    bytes_count: int


@dataclass(frozen=True)
class PackageFingerprint:
    """Resolved version of a tracked package, or 'not_installed'."""

    name: str
    version: str


@dataclass
class ReproducibilityManifest:
    """A reviewer-readable record of *how* a Tier 1 case was produced."""

    case_id: str
    generated_at_utc: str
    claim_tier: str
    claim_boundary: str
    git_commit_sha: str | None
    git_branch: str | None
    git_dirty: bool
    python_version: str
    python_implementation: str
    platform_summary: str
    tracked_packages: list[PackageFingerprint]
    scripts: list[ScriptFingerprint]
    tier2_blockers_remaining: list[str]
    claim_impact: str


@dataclass(frozen=True)
class ReproducibilityManifestInputs:
    """Builder inputs for a single Tier 1 candidate case."""

    case_id: str
    repo_root: Path
    generator_script_path: Path | None = None
    additional_script_paths: tuple[Path, ...] = ()


def build_reproducibility_manifest(
    inputs: ReproducibilityManifestInputs,
) -> ReproducibilityManifest:
    """Capture environment + script fingerprints for one Tier 1 case."""
    repo_root = inputs.repo_root.resolve()

    git_commit, git_branch, git_dirty = _git_state(repo_root)
    packages = [_package_fingerprint(name) for name in _TRACKED_PACKAGES]

    scripts: list[ScriptFingerprint] = []
    seen: set[Path] = set()
    candidate_paths: list[Path] = []
    if inputs.generator_script_path is not None:
        candidate_paths.append(inputs.generator_script_path)
    candidate_paths.extend(inputs.additional_script_paths)
    for path in candidate_paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        fingerprint = _script_fingerprint(resolved, repo_root)
        if fingerprint is not None:
            scripts.append(fingerprint)

    manifest = ReproducibilityManifest(
        case_id=inputs.case_id,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        git_commit_sha=git_commit,
        git_branch=git_branch,
        git_dirty=git_dirty,
        python_version=platform.python_version(),
        python_implementation=platform.python_implementation(),
        platform_summary=platform.platform(),
        tracked_packages=packages,
        scripts=scripts,
        tier2_blockers_remaining=[
            "FM-04b P8 sealed packet (immutable dependency lockfile + reviewer signoff)",
            "ADR-024 full citation of solver dependency versions",
        ],
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(manifest)
    return manifest


def render_reproducibility_manifest_json(manifest: ReproducibilityManifest) -> str:
    """Return the manifest as a JSON string."""
    return json.dumps(_manifest_to_dict(manifest), indent=2, sort_keys=True)


def write_reproducibility_manifest(
    manifest: ReproducibilityManifest, output_dir: Path | str
) -> Path:
    """Write the manifest to ``output_dir / "reproducibility_manifest.json"``.

    Refuses to write under ``golden_samples/**``.
    """
    out_dir = Path(output_dir)
    _assert_not_in_golden_samples(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "reproducibility_manifest.json"
    out_path.write_text(render_reproducibility_manifest_json(manifest), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


def _git_state(repo_root: Path) -> tuple[str | None, str | None, bool]:
    if not (repo_root / ".git").exists():
        return None, None, False
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        commit = None
    try:
        branch = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        branch = None
    try:
        status = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
        dirty = bool(status.strip())
    except (subprocess.SubprocessError, FileNotFoundError):
        dirty = False
    return commit or None, branch or None, dirty


def _package_fingerprint(name: str) -> PackageFingerprint:
    try:
        version = importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        version = "not_installed"
    return PackageFingerprint(name=name, version=version)


def _script_fingerprint(path: Path, repo_root: Path) -> ScriptFingerprint | None:
    if not path.is_file():
        return None
    raw = path.read_bytes()
    relpath = _relpath(path, repo_root)
    return ScriptFingerprint(
        relpath=relpath,
        sha256=hashlib.sha256(raw).hexdigest(),
        bytes_count=len(raw),
    )


def _relpath(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _manifest_to_dict(manifest: ReproducibilityManifest) -> dict[str, Any]:
    return {
        "schema_version": REPRODUCIBILITY_MANIFEST_SCHEMA_VERSION,
        "case_id": manifest.case_id,
        "generated_at_utc": manifest.generated_at_utc,
        "claim_tier": manifest.claim_tier,
        "claim_boundary": manifest.claim_boundary,
        "git_commit_sha": manifest.git_commit_sha,
        "git_branch": manifest.git_branch,
        "git_dirty": manifest.git_dirty,
        "python_version": manifest.python_version,
        "python_implementation": manifest.python_implementation,
        "platform_summary": manifest.platform_summary,
        "tracked_packages": [
            {"name": p.name, "version": p.version} for p in manifest.tracked_packages
        ],
        "scripts": [
            {"relpath": s.relpath, "sha256": s.sha256, "bytes": s.bytes_count}
            for s in manifest.scripts
        ],
        "tier2_blockers_remaining": manifest.tier2_blockers_remaining,
        "claim_impact": manifest.claim_impact,
    }


def _assert_no_overclaim(manifest: ReproducibilityManifest) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(_manifest_to_dict(manifest), default=str).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(
                f"Reproducibility manifest contains forbidden positive claim: {token!r}"
            )


def _assert_not_in_golden_samples(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    for parent in (resolved, *resolved.parents):
        if parent.name == "golden_samples":
            raise ValueError(
                "Reproducibility manifest refuses writes under golden_samples/**; "
                "use reports/ or project_state/<...>/ instead"
            )
