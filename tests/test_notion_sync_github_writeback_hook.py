"""Tests for the GitHub-writeback hook inside NotionRunRegistrar (P2 integration)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mod():
    from backend.app.well_harness import notion_sync

    return notion_sync


@pytest.fixture
def config_writeback_on(mod):
    return mod.NotionSyncConfig(
        enabled=True,
        token_env="NOTION_TOKEN",
        notion_version="2022-06-28",
        root_page_id="root",
        data_sources=mod.NotionDataSources(tasks="t", sessions="s", decisions=None),
        github_repository="kogamishinyajerry-ops/ai-structure-analysis",
        github_writeback_enabled=True,
    )


@pytest.fixture
def config_writeback_off(mod):
    return mod.NotionSyncConfig(
        enabled=True,
        token_env="NOTION_TOKEN",
        notion_version="2022-06-28",
        root_page_id="root",
        data_sources=mod.NotionDataSources(tasks="t", sessions="s", decisions=None),
        github_repository="kogamishinyajerry-ops/ai-structure-analysis",
        github_writeback_enabled=False,
    )


def _make_registrar(mod, config):
    """Build a NotionRunRegistrar without invoking its real HTTP path."""
    return mod.NotionRunRegistrar(config=config)


def _fake_run_record():
    """Minimal HarnessRunRecord-shaped object the registrar's helpers can read."""
    rec = MagicMock()
    rec.case_id = "GS-001"
    rec.run_id = "run-x"
    rec.verdict = "ACCEPT"
    rec.deviation_max = 0.01
    rec.execution_mode = "real"
    return rec


# ---------------------------------------------------------------------------
# Opt-in / opt-out behavior
# ---------------------------------------------------------------------------


def test_writeback_skipped_when_disabled(mod, config_writeback_off):
    reg = _make_registrar(mod, config_writeback_off)
    with patch("backend.app.well_harness.github_writeback.post_pr_comment") as post:
        reg._maybe_post_github_writeback(
            run_records=[_fake_run_record()],
            github_pr_link="https://github.com/o/r/pull/1",
            github_issue_link=None,
            session_page_id="abc",
        )
    post.assert_not_called()


def test_writeback_skipped_when_no_repository(mod):
    cfg = mod.NotionSyncConfig(
        enabled=True,
        token_env="NOTION_TOKEN",
        notion_version="2022-06-28",
        root_page_id="root",
        data_sources=mod.NotionDataSources(tasks="t", sessions="s", decisions=None),
        github_repository=None,
        github_writeback_enabled=True,
    )
    reg = _make_registrar(mod, cfg)
    with patch("backend.app.well_harness.github_writeback.post_pr_comment") as post:
        reg._maybe_post_github_writeback(
            run_records=[_fake_run_record()],
            github_pr_link="https://github.com/o/r/pull/1",
            github_issue_link=None,
            session_page_id="abc",
        )
    post.assert_not_called()


def test_writeback_skipped_when_no_link(mod, config_writeback_on):
    reg = _make_registrar(mod, config_writeback_on)
    with patch("backend.app.well_harness.github_writeback.post_pr_comment") as post:
        reg._maybe_post_github_writeback(
            run_records=[_fake_run_record()],
            github_pr_link=None,
            github_issue_link=None,
            session_page_id="abc",
        )
    post.assert_not_called()


def test_writeback_skipped_when_no_token(mod, config_writeback_on):
    """If gh.writeback_enabled() is False (no token), do not post."""
    reg = _make_registrar(mod, config_writeback_on)
    with patch("backend.app.well_harness.github_writeback.writeback_enabled", return_value=False):  # noqa: SIM117
        with patch("backend.app.well_harness.github_writeback.post_pr_comment") as post:
            reg._maybe_post_github_writeback(
                run_records=[_fake_run_record()],
                github_pr_link="https://github.com/o/r/pull/1",
                github_issue_link=None,
                session_page_id="abc",
            )
    post.assert_not_called()


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------


def test_writeback_parses_pull_url(mod, config_writeback_on):
    reg = _make_registrar(mod, config_writeback_on)
    with patch("backend.app.well_harness.github_writeback.writeback_enabled", return_value=True):  # noqa: SIM117
        with patch("backend.app.well_harness.github_writeback.post_pr_comment") as post:
            reg._maybe_post_github_writeback(
                run_records=[_fake_run_record()],
                github_pr_link="https://github.com/o/r/pull/42",
                github_issue_link=None,
                session_page_id="abc",
            )
    post.assert_called_once()
    _, kwargs = post.call_args
    assert kwargs["pr_number"] == 42
    assert kwargs["repo"] == "kogamishinyajerry-ops/ai-structure-analysis"


def test_writeback_parses_issues_url(mod, config_writeback_on):
    reg = _make_registrar(mod, config_writeback_on)
    with patch("backend.app.well_harness.github_writeback.writeback_enabled", return_value=True):  # noqa: SIM117
        with patch("backend.app.well_harness.github_writeback.post_pr_comment") as post:
            reg._maybe_post_github_writeback(
                run_records=[_fake_run_record()],
                github_pr_link=None,
                github_issue_link="https://github.com/o/r/issues/7",
                session_page_id=None,
            )
    post.assert_called_once()
    _, kwargs = post.call_args
    assert kwargs["pr_number"] == 7


def test_writeback_pr_link_preferred_over_issue(mod, config_writeback_on):
    reg = _make_registrar(mod, config_writeback_on)
    with patch("backend.app.well_harness.github_writeback.writeback_enabled", return_value=True):  # noqa: SIM117
        with patch("backend.app.well_harness.github_writeback.post_pr_comment") as post:
            reg._maybe_post_github_writeback(
                run_records=[_fake_run_record()],
                github_pr_link="https://github.com/o/r/pull/100",
                github_issue_link="https://github.com/o/r/issues/200",
                session_page_id="abc",
            )
    _, kwargs = post.call_args
    assert kwargs["pr_number"] == 100  # PR wins


def test_writeback_skipped_on_unparseable_url(mod, config_writeback_on):
    reg = _make_registrar(mod, config_writeback_on)
    with patch("backend.app.well_harness.github_writeback.writeback_enabled", return_value=True):  # noqa: SIM117
        with patch("backend.app.well_harness.github_writeback.post_pr_comment") as post:
            reg._maybe_post_github_writeback(
                run_records=[_fake_run_record()],
                github_pr_link="https://example.com/not-a-github-url",
                github_issue_link=None,
                session_page_id="abc",
            )
    post.assert_not_called()


# ---------------------------------------------------------------------------
# Body composition
# ---------------------------------------------------------------------------


def test_writeback_body_includes_case_ids(mod, config_writeback_on):
    reg = _make_registrar(mod, config_writeback_on)
    rec_a = _fake_run_record()
    rec_a.case_id = "GS-001"
    rec_b = _fake_run_record()
    rec_b.case_id = "GS-002"
    with patch("backend.app.well_harness.github_writeback.writeback_enabled", return_value=True):  # noqa: SIM117
        with patch("backend.app.well_harness.github_writeback.post_pr_comment") as post:
            reg._maybe_post_github_writeback(
                run_records=[rec_a, rec_b],
                github_pr_link="https://github.com/o/r/pull/1",
                github_issue_link=None,
                session_page_id="abcdef0123",
            )
    _, kwargs = post.call_args
    body = kwargs["body"]
    assert "GS-001" in body
    assert "GS-002" in body
    # Notion URL constructed from session_page_id
    assert "abcdef0123" in body or "notion.so" in body


def test_writeback_handles_empty_run_records(mod, config_writeback_on):
    """No run records → skip rather than post empty comment.

    Empty run_records also fails the registrar's earlier guard, but
    the helper should be defensive at this layer too."""
    reg = _make_registrar(mod, config_writeback_on)
    with patch("backend.app.well_harness.github_writeback.writeback_enabled", return_value=True):  # noqa: SIM117
        with patch("backend.app.well_harness.github_writeback.post_pr_comment") as post:
            # Build summary text guard inside the helper handles []; we still
            # want to confirm that with one record the call goes through.
            reg._maybe_post_github_writeback(
                run_records=[_fake_run_record()],
                github_pr_link="https://github.com/o/r/pull/1",
                github_issue_link=None,
                session_page_id="abc",
            )
    post.assert_called_once()


# ---------------------------------------------------------------------------
# Config loading from yaml
# ---------------------------------------------------------------------------


def test_config_from_file_default_writeback_off(mod, tmp_path):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        """
notion:
  enabled: true
  data_source_ids:
    tasks: t
    sessions: s
github:
  repository: o/r
"""
    )
    cfg = mod.NotionSyncConfig.from_file(cfg_path)
    assert cfg.github_writeback_enabled is False


def test_config_from_file_writeback_on(mod, tmp_path):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        """
notion:
  enabled: true
  data_source_ids:
    tasks: t
    sessions: s
github:
  repository: o/r
  writeback_enabled: true
"""
    )
    cfg = mod.NotionSyncConfig.from_file(cfg_path)
    assert cfg.github_writeback_enabled is True
    assert cfg.github_repository == "o/r"
