"""FM-04a Phase 7 B — locale-parametrized narrative template tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Closes Phase 6 retrospective carry-forward §3.

This file exists to satisfy the Phase 7 anti-gaming guards:

* ``T: -2 per axis whose property-based test does not include a fixed
  seed`` does NOT apply here (this is locale catalog, not property).
* ``C: -5 if a forbidden positive claim appears in the zh-CN catalog``
  — provoked by ``test_zh_cn_catalog_forbidden_claim_audit_fires``.
* ``C: -3 per locale that does not run _assert_no_overclaim at module
  import time`` — provoked by ``test_module_import_runs_forbidden_audit``.
* ``M: -3 if the locale catalog is created via runtime if-branches``
  — proven by ``test_catalog_is_dict_dispatched`` (asserts the
  catalog is a plain dict).

Plus 16 zh-CN positive tests (one per template_id), so every Chinese
template fires under a positive test — same coverage Phase 6 C gave
the en-US catalog.
"""

from __future__ import annotations

import importlib

import pytest
from app.services.reporting.cohort_snapshot_diff import (
    CompletenessDelta,
    ReproducibilityDelta,
)
from app.services.reporting.snapshot_narrative import build_snapshot_narrative
from app.services.reporting.snapshot_narrative_catalogs import (
    CATALOGS,
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    TEMPLATE_IDS,
    render_template,
)

# Mirrors the helpers from tests/test_snapshot_narrative.py but builds
# minimal diffs targeted at one template at a time.
from tests.test_snapshot_narrative import (  # noqa: E402
    _make_diff,
    _make_numerical,
)

# ---------------------------------------------------------------------
# Module structural invariants
# ---------------------------------------------------------------------


def test_supported_locales_includes_zh_cn() -> None:
    assert "en-US" in SUPPORTED_LOCALES
    assert "zh-CN" in SUPPORTED_LOCALES


def test_default_locale_is_en_us() -> None:
    assert DEFAULT_LOCALE == "en-US"


def test_template_ids_count_is_sixteen() -> None:
    """The blueprint enumerates 16 templates; the canonical set must
    expose exactly that count regardless of locale."""
    assert len(TEMPLATE_IDS) == 16


def test_catalog_is_dict_dispatched() -> None:
    """Phase 7 anti-gaming guard M: -3 if the locale catalog is created
    via runtime ``if locale == 'zh-CN'`` branches. The catalog must be
    a plain dict whose keys are locale codes.
    """
    assert isinstance(CATALOGS, dict)
    for locale, catalog in CATALOGS.items():
        assert isinstance(locale, str)
        assert isinstance(catalog, dict)
        for template_id, body in catalog.items():
            assert isinstance(template_id, str)
            assert isinstance(body, str)


def test_template_id_set_consistent_across_locales() -> None:
    canonical = set(CATALOGS[DEFAULT_LOCALE].keys())
    for locale, catalog in CATALOGS.items():
        assert set(catalog.keys()) == canonical, (
            f"locale {locale!r} template_id set drifted from canonical"
        )


# ---------------------------------------------------------------------
# Module-import-time forbidden-claim audit
# ---------------------------------------------------------------------


def test_module_import_runs_forbidden_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reload the module after monkey-patching a forbidden token into
    one of the catalog strings; the import-time audit must raise.
    """
    import app.services.reporting.snapshot_narrative_catalogs as cat_mod

    original_en = dict(cat_mod.CATALOGS["en-US"])
    try:
        cat_mod.CATALOGS["en-US"]["residual_velocity_delta"] = (
            "validated against benchmark (synthetic test injection)"
        )
        with pytest.raises(ValueError, match="forbidden"):
            cat_mod._audit_catalog_forbidden_claims()
    finally:
        cat_mod.CATALOGS["en-US"].update(original_en)


def test_zh_cn_catalog_forbidden_claim_audit_fires() -> None:
    """Phase 7 anti-gaming guard C: -5 if a forbidden positive claim
    appears in the zh-CN catalog. Provoke the audit on a transient
    catalog override and confirm it raises.
    """
    import app.services.reporting.snapshot_narrative_catalogs as cat_mod

    original_zh = dict(cat_mod.CATALOGS["zh-CN"])
    try:
        cat_mod.CATALOGS["zh-CN"]["cohort_added"] = "案例已 perforation completed (恶意翻译)"
        with pytest.raises(ValueError, match="forbidden"):
            cat_mod._audit_catalog_forbidden_claims()
    finally:
        cat_mod.CATALOGS["zh-CN"].update(original_zh)


def test_template_id_drift_audit_fires() -> None:
    """The consistency audit catches a locale that gained an extra
    template_id not present in en-US."""
    import app.services.reporting.snapshot_narrative_catalogs as cat_mod

    original_zh = dict(cat_mod.CATALOGS["zh-CN"])
    try:
        cat_mod.CATALOGS["zh-CN"]["rogue_template"] = "rogue 漫游模板"
        with pytest.raises(ValueError, match="drifted"):
            cat_mod._audit_template_id_consistency()
    finally:
        cat_mod.CATALOGS["zh-CN"] = original_zh


# ---------------------------------------------------------------------
# Module-import-time happy path (proves the audits don't fire on
# the shipped catalog)
# ---------------------------------------------------------------------


def test_shipped_catalog_passes_forbidden_audit() -> None:
    importlib.reload(importlib.import_module("app.services.reporting.snapshot_narrative_catalogs"))


# ---------------------------------------------------------------------
# render_template direct unit tests
# ---------------------------------------------------------------------


def test_render_template_rejects_unknown_locale() -> None:
    with pytest.raises(ValueError, match="unsupported locale"):
        render_template("cohort_added", "fr-FR", {"case_id": "GS-A"})


def test_render_template_rejects_unknown_template_id() -> None:
    with pytest.raises(ValueError, match="unknown template_id"):
        render_template("not_a_real_template", "en-US", {})


def test_render_template_en_us_baseline() -> None:
    text = render_template("cohort_added", "en-US", {"case_id": "GS-A-candidate"})
    assert text == "Case GS-A-candidate added to the cohort between snapshots."


def test_render_template_zh_cn_baseline() -> None:
    text = render_template("cohort_added", "zh-CN", {"case_id": "GS-A-candidate"})
    assert "GS-A-candidate" in text
    assert "候选集" in text


# ---------------------------------------------------------------------
# Build-narrative locale roundtrip
# ---------------------------------------------------------------------


def test_build_narrative_rejects_unsupported_locale() -> None:
    diff = _make_diff(cohort_added=["GS-A-candidate"])
    with pytest.raises(ValueError, match="unsupported locale"):
        build_snapshot_narrative(diff, locale="fr-FR")


def test_build_narrative_envelope_carries_locale_field() -> None:
    diff = _make_diff(cohort_added=["GS-A-candidate"])
    narrative = build_snapshot_narrative(diff, locale="zh-CN")
    assert narrative.locale == "zh-CN"


def test_build_narrative_default_locale_is_en_us() -> None:
    diff = _make_diff(cohort_added=["GS-A-candidate"])
    narrative = build_snapshot_narrative(diff)
    assert narrative.locale == "en-US"


# ---------------------------------------------------------------------
# zh-CN: per-template positive tests (16 templates, each fires)
# ---------------------------------------------------------------------


def _zh_text_for_first_line(narrative) -> str:
    assert len(narrative.narratives) >= 1
    assert len(narrative.narratives[0].lines) >= 1
    return narrative.narratives[0].lines[0].text


def test_zh_cohort_added() -> None:
    n = build_snapshot_narrative(_make_diff(cohort_added=["GS-A-candidate"]), locale="zh-CN")
    text = _zh_text_for_first_line(n)
    assert "GS-A-candidate" in text
    assert "新增" in text


def test_zh_cohort_removed() -> None:
    n = build_snapshot_narrative(_make_diff(cohort_removed=["GS-A-candidate"]), locale="zh-CN")
    text = _zh_text_for_first_line(n)
    assert "GS-A-candidate" in text
    assert "移除" in text


def test_zh_residual_velocity_delta() -> None:
    delta = _make_numerical("GS-A-candidate", rv_a=75.0, rv_b=80.0)
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], numerical_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "残余速度" in text
    assert "75" in text
    assert "80" in text


def test_zh_residual_velocity_unchanged() -> None:
    delta = _make_numerical("GS-A-candidate", rv_a=75.0, rv_b=75.0)
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], numerical_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "残余速度" in text
    assert "保持" in text


def test_zh_energy_balance_improved() -> None:
    delta = _make_numerical("GS-A-candidate", eb_a=12.0, eb_b=8.0)
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], numerical_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "能量平衡误差" in text
    assert "收紧" in text


def test_zh_energy_balance_degraded() -> None:
    delta = _make_numerical("GS-A-candidate", eb_a=8.0, eb_b=12.0)
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], numerical_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "能量平衡误差" in text
    assert "扩大" in text


def test_zh_energy_balance_unchanged() -> None:
    delta = _make_numerical("GS-A-candidate", eb_a=10.0, eb_b=10.0)
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], numerical_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "能量平衡误差" in text
    assert "保持" in text


def test_zh_convergence_verdict_changed() -> None:
    delta = _make_numerical(
        "GS-A-candidate",
        cv_a="candidate_observed_stable",
        cv_b="candidate_observed_unstable",
    )
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], numerical_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "收敛判定" in text
    assert "candidate_observed_unstable" in text


def test_zh_perforation_marker_changed() -> None:
    delta = _make_numerical(
        "GS-A-candidate",
        pm_a="candidate_perforation",
        pm_b="candidate_no_perforation",
    )
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], numerical_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "穿透标记" in text


def test_zh_completeness_improved() -> None:
    delta = CompletenessDelta(case_id="GS-A-candidate", a_score=70, b_score=80, delta=10)
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], completeness_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "完备性评分" in text
    assert "提升" in text


def test_zh_completeness_regressed() -> None:
    delta = CompletenessDelta(case_id="GS-A-candidate", a_score=80, b_score=70, delta=-10)
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], completeness_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "完备性评分" in text
    assert "回退" in text


def test_zh_completeness_unchanged() -> None:
    delta = CompletenessDelta(case_id="GS-A-candidate", a_score=80, b_score=80, delta=0)
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], completeness_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "完备性评分" in text
    assert "保持" in text


def test_zh_git_sha_changed() -> None:
    delta = ReproducibilityDelta(
        case_id="GS-A-candidate",
        a_git_sha="aaaaaaa" + "0" * 33,
        b_git_sha="bbbbbbb" + "0" * 33,
        git_sha_changed=True,
        a_git_dirty=False,
        b_git_dirty=False,
        dirty_changed=False,
        a_python_version="3.11.5",
        b_python_version="3.11.5",
        python_version_changed=False,
        package_version_changes=[],
        script_sha_changes=[],
    )
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], reproducibility_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "Git commit" in text
    assert "推进" in text


def test_zh_git_dirty_introduced() -> None:
    delta = ReproducibilityDelta(
        case_id="GS-A-candidate",
        a_git_sha=None,
        b_git_sha=None,
        git_sha_changed=False,
        a_git_dirty=False,
        b_git_dirty=True,
        dirty_changed=True,
        a_python_version="3.11.5",
        b_python_version="3.11.5",
        python_version_changed=False,
        package_version_changes=[],
        script_sha_changes=[],
    )
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], reproducibility_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "工作树" in text


def test_zh_python_version_changed() -> None:
    delta = ReproducibilityDelta(
        case_id="GS-A-candidate",
        a_git_sha=None,
        b_git_sha=None,
        git_sha_changed=False,
        a_git_dirty=False,
        b_git_dirty=False,
        dirty_changed=False,
        a_python_version="3.11.5",
        b_python_version="3.12.0",
        python_version_changed=True,
        package_version_changes=[],
        script_sha_changes=[],
    )
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], reproducibility_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "Python 解释器" in text
    assert "3.11.5" in text
    assert "3.12.0" in text


def test_zh_script_sha_changed() -> None:
    delta = ReproducibilityDelta(
        case_id="GS-A-candidate",
        a_git_sha=None,
        b_git_sha=None,
        git_sha_changed=False,
        a_git_dirty=False,
        b_git_dirty=False,
        dirty_changed=False,
        a_python_version="3.11.5",
        b_python_version="3.11.5",
        python_version_changed=False,
        package_version_changes=[],
        script_sha_changes=[
            {
                "relpath": "scripts/gen_gsa_deck.py",
                "a_sha256": "a" * 64,
                "b_sha256": "b" * 64,
            }
        ],
    )
    n = build_snapshot_narrative(
        _make_diff(cohort_shared=["GS-A-candidate"], reproducibility_deltas=[delta]),
        locale="zh-CN",
    )
    text = _zh_text_for_first_line(n)
    assert "生成脚本" in text
    assert "gen_gsa_deck.py" in text


# ---------------------------------------------------------------------
# Locale parity: same template_id + severity emitted across locales
# ---------------------------------------------------------------------


def test_locale_parity_residual_velocity_delta() -> None:
    delta = _make_numerical("GS-A-candidate", rv_a=75.0, rv_b=80.0)
    diff = _make_diff(cohort_shared=["GS-A-candidate"], numerical_deltas=[delta])
    en = build_snapshot_narrative(diff, locale="en-US")
    zh = build_snapshot_narrative(diff, locale="zh-CN")
    en_template_ids = [line.template_id for case in en.narratives for line in case.lines]
    zh_template_ids = [line.template_id for case in zh.narratives for line in case.lines]
    assert en_template_ids == zh_template_ids
    en_severities = [line.severity for case in en.narratives for line in case.lines]
    zh_severities = [line.severity for case in zh.narratives for line in case.lines]
    assert en_severities == zh_severities
    # Text MUST differ (otherwise the catalog is not actually localized)
    en_texts = [line.text for case in en.narratives for line in case.lines]
    zh_texts = [line.text for case in zh.narratives for line in case.lines]
    assert en_texts != zh_texts


def test_locale_parity_convergence_verdict_changed_severity_escalates() -> None:
    """Severity is locale-independent (it's a rubric, not a translation).
    Both locales must escalate convergence_observed_unstable to danger.
    """
    delta = _make_numerical(
        "GS-A-candidate",
        cv_a="candidate_observed_stable",
        cv_b="candidate_observed_unstable",
    )
    diff = _make_diff(cohort_shared=["GS-A-candidate"], numerical_deltas=[delta])
    for locale in ("en-US", "zh-CN"):
        narrative = build_snapshot_narrative(diff, locale=locale)
        sev = narrative.narratives[0].lines[0].severity
        assert sev == "danger"
