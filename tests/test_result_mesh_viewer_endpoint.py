from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.api.routes._viz_helpers import (
    _resolve_result_mesh_artifact_path,
    _validate_case_id,
)


def test_resolve_result_mesh_artifact_path_stays_under_project_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # FM-04a Phase 41.4: artifact resolution now anchors to the repo root
    # (file-anchored, cwd-independent) instead of Path.cwd(). Pin _repo_root to
    # a controlled tmp root — the prior `monkeypatch.chdir(tmp_path)` exercised
    # the exact cwd-dependence this fix removed (the result-mesh route 404'd
    # whenever uvicorn was launched from anywhere but the repo root).
    monkeypatch.setattr("app.api.routes._viz_helpers._repo_root", lambda: tmp_path)
    target = tmp_path / "project_state" / "visualizations" / "CASE-VIEW" / "result_mesh.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"schemaVersion": 1}), encoding="utf-8")

    resolved = _resolve_result_mesh_artifact_path("CASE-VIEW", "result_mesh.json")

    assert resolved == target.resolve()


def test_resolve_result_mesh_artifact_path_refuses_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.routes._viz_helpers._repo_root", lambda: tmp_path)
    (tmp_path / "project_state" / "visualizations" / "CASE-VIEW").mkdir(parents=True)

    with pytest.raises(ValueError, match="unsupported result-mesh artifact"):
        _resolve_result_mesh_artifact_path("CASE-VIEW", "../secret.json")

    with pytest.raises(ValueError, match="invalid shape"):
        _validate_case_id("../../bad")
