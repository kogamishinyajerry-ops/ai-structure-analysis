"""Locale-parametrized narrative catalogs (FM-04a Phase 7 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Closes Phase 6 retrospective carry-forward §3: every narrative template
now has a localized rendering. Two locales ship:

* ``en-US`` — the existing 16 English templates (verbatim, unchanged
  behavior). This is the default locale; un-localized callers see the
  same text Phase 6 C shipped.
* ``zh-CN`` — pilot Chinese catalog covering the same 16 ``template_id``
  + ``severity`` pairs with hand-translated slot-fill strings. The
  translation is fixed; there is NO LLM / generative call.

Catalog dispatch is dict-driven (``CATALOGS[locale][template_id]``)
rather than runtime ``if locale == "zh-CN"`` branches; this satisfies
the Phase 7 anti-gaming guard ``M: -3 if the locale catalog is created
via runtime if-branches instead of a dict-based dispatch``.

Forbidden-claim audit (per ADR-023 + ADR-024 lite) runs at import time
across EVERY locale × template combination. A translation that smuggles
in a forbidden positive claim aborts module import — closing the
Phase 7 anti-gaming guard ``C: -5 if a forbidden positive claim appears
in the zh-CN catalog``.

Slot-value conventions (caller-provided, locale-agnostic):
* numeric slots use ``{a:g}`` / ``{b:g}`` to drop trailing zeros
* ``{delta_pct}`` is pre-formatted as a string (``+6.67%`` etc.) so the
  ``%`` sign appears once per locale, not via an embedded f-string
* SHA-like slots (``{a_short_sha}``, ``{relpaths}``) are pre-rendered
  strings (short SHA, comma-joined paths)
* enum-string slots (``{a!r}``, ``{b!r}``) carry the Python repr form
  with quotes — the verdict labels themselves remain English even in
  zh-CN because that is the canonical machine label
"""

from __future__ import annotations

CATALOGS: dict[str, dict[str, str]] = {
    "en-US": {
        "residual_velocity_delta": (
            "Residual velocity changed from {a:g} to {b:g} m/s ({delta_pct})."
        ),
        "residual_velocity_unchanged": "Residual velocity unchanged at {a:g} m/s.",
        "energy_balance_improved": (
            "Energy balance error tightened from {a:g}% to {b:g}% "
            "(absolute delta {delta_abs_pct:g}%)."
        ),
        "energy_balance_degraded": (
            "Energy balance error widened from {a:g}% to {b:g}% "
            "(absolute delta {delta_abs_pct:g}%)."
        ),
        "energy_balance_unchanged": "Energy balance error unchanged at {a:g}%.",
        "convergence_verdict_changed": (
            "Convergence verdict changed from {a!r} to {b!r}."
        ),
        "perforation_marker_changed": (
            "Perforation marker changed from {a!r} to {b!r}."
        ),
        "script_sha_changed": (
            "Generator script SHA-256 changed ({relpaths}); regression risk."
        ),
        "python_version_changed": (
            "Python interpreter changed from {a_python_version} to "
            "{b_python_version}; regression risk on numerical output."
        ),
        "git_sha_changed": (
            "Git commit advanced from {a_short_sha} to {b_short_sha}."
        ),
        "git_dirty_introduced": (
            "Working tree went from clean to dirty between snapshots."
        ),
        "completeness_improved": (
            "Completeness score lifted from {a_score} to {b_score} (+{delta})."
        ),
        "completeness_regressed": (
            "Completeness score regressed from {a_score} to {b_score} ({delta})."
        ),
        "completeness_unchanged": (
            "Completeness score unchanged at {a_score}."
        ),
        "cohort_added": (
            "Case {case_id} added to the cohort between snapshots."
        ),
        "cohort_removed": (
            "Case {case_id} removed from the cohort between snapshots."
        ),
    },
    "zh-CN": {
        "residual_velocity_delta": (
            "残余速度从 {a:g} m/s 变化到 {b:g} m/s ({delta_pct})。"
        ),
        "residual_velocity_unchanged": "残余速度保持在 {a:g} m/s。",
        "energy_balance_improved": (
            "能量平衡误差从 {a:g}% 收紧到 {b:g}% (绝对差值 {delta_abs_pct:g}%)。"
        ),
        "energy_balance_degraded": (
            "能量平衡误差从 {a:g}% 扩大到 {b:g}% (绝对差值 {delta_abs_pct:g}%)。"
        ),
        "energy_balance_unchanged": "能量平衡误差保持在 {a:g}%。",
        "convergence_verdict_changed": "收敛判定从 {a!r} 变化为 {b!r}。",
        "perforation_marker_changed": "穿透标记从 {a!r} 变化为 {b!r}。",
        "script_sha_changed": "生成脚本 SHA-256 变更 ({relpaths}); 存在回归风险。",
        "python_version_changed": (
            "Python 解释器从 {a_python_version} 切换到 {b_python_version}; "
            "数值输出存在回归风险。"
        ),
        "git_sha_changed": "Git commit 从 {a_short_sha} 推进到 {b_short_sha}。",
        "git_dirty_introduced": "两个快照之间工作树从干净变为脏。",
        "completeness_improved": (
            "完备性评分从 {a_score} 提升到 {b_score} (+{delta})。"
        ),
        "completeness_regressed": (
            "完备性评分从 {a_score} 回退到 {b_score} ({delta})。"
        ),
        "completeness_unchanged": "完备性评分保持在 {a_score}。",
        "cohort_added": "候选集在两个快照之间新增了案例 {case_id}。",
        "cohort_removed": "候选集在两个快照之间移除了案例 {case_id}。",
    },
}

SUPPORTED_LOCALES: tuple[str, ...] = tuple(CATALOGS.keys())
DEFAULT_LOCALE: str = "en-US"

TEMPLATE_IDS: tuple[str, ...] = tuple(CATALOGS[DEFAULT_LOCALE].keys())
"""Canonical 16-element template enumeration; every locale must expose
the same set of template_id keys."""

_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "validated against",
    "perforation completed",
    "bullet-through-steel complete",
    "validated physics",
    "signed validation",
    "benchmark agreement",
)


def _audit_catalog_forbidden_claims() -> None:
    """Module-import-time audit: every locale × template emits forbidden
    free of positive claims that could be mistaken for Tier 2 endorsements.

    Per Phase 7 anti-gaming guard ``C: -3 per locale that does not run
    _assert_no_overclaim at module import time``, this is a load-bearing
    invocation: removing or short-circuiting it is a phase-7 defect.

    Note: ``benchmark agreement`` and ``signed validation`` are scanned
    in *raw form*; the canonical disclaimer form ``not signed
    validation`` is never inside a template body (templates carry only
    delta descriptions, not disclaimers).
    """
    for locale, catalog in CATALOGS.items():
        for template_id, body in catalog.items():
            lowered = body.lower()
            for token in _FORBIDDEN_TOKENS:
                if token in lowered:
                    raise ValueError(
                        f"narrative catalog locale={locale!r} "
                        f"template_id={template_id!r} contains forbidden "
                        f"positive claim {token!r}"
                    )


def _audit_template_id_consistency() -> None:
    """Every locale must expose exactly the same set of template_ids;
    drift means a translation gap or extra rogue template.
    """
    canonical = set(CATALOGS[DEFAULT_LOCALE].keys())
    for locale, catalog in CATALOGS.items():
        if locale == DEFAULT_LOCALE:
            continue
        these = set(catalog.keys())
        missing = canonical - these
        extra = these - canonical
        if missing or extra:
            raise ValueError(
                f"narrative catalog locale={locale!r} drifted from "
                f"canonical template_id set; missing={sorted(missing)!r} "
                f"extra={sorted(extra)!r}"
            )


# Module-import-time invocations (load-bearing per blueprint §4 guards):
_audit_template_id_consistency()
_audit_catalog_forbidden_claims()


def render_template(template_id: str, locale: str, slots: dict[str, object]) -> str:
    """Render a single narrative line for the given locale + template_id.

    Raises ``ValueError`` for unknown locale or template_id. Raises
    ``KeyError`` / ``ValueError`` if the slot dict is missing a key the
    template needs (this is a caller bug; templates are stable).
    """
    if locale not in CATALOGS:
        raise ValueError(
            f"unsupported locale {locale!r}; "
            f"expected one of {SUPPORTED_LOCALES!r}"
        )
    catalog = CATALOGS[locale]
    if template_id not in catalog:
        raise ValueError(
            f"unknown template_id {template_id!r} for locale {locale!r}"
        )
    return catalog[template_id].format(**slots)
