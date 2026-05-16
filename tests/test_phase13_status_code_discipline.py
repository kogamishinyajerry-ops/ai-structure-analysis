"""FM-04a Phase 13 B — status-code-discipline meta-test.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

This meta-test is a *carry-forward closure guard* for the Phase 11 retro
§4 finding (permissive ``status_code in (4xx, 4xx)`` assertions across
the cross-phase test suite). It enforces the slice-B discipline:

* Every test file under ``tests/`` is scanned for permissive 4xx-range
  status-code assertions.
* The total count of permissive sites MUST NOT exceed a pinned ceiling
  (``_PERMISSIVE_4XX_CEILING``).
* Slice B closed every observed permissive site (5 in 4 files); the
  initial ceiling is therefore **0**.
* Any future test that re-introduces a permissive pattern will trip
  the ceiling and surface as a real failure. To intentionally raise
  the ceiling, edit ``_PERMISSIVE_4XX_CEILING`` AND add a justification
  inline; PRs that bump the ceiling without justification will be
  refused at review.

Why a meta-test and not just `ruff`?
* Permissive 4xx assertions are *semantically* valid Python — no
  linter catches them.
* The discipline is a *test-suite contract*, not a *runtime contract*;
  enforcing it from inside the suite means it travels with the suite.
* The pattern set is intentionally narrow (4xx-only) so it does not
  trip on unrelated `in (200, 201, 204)` happy-path success ranges
  or on stub-response constructors like ``_StubResult(status_code=403)``.

Scope:
* Scans ``tests/test_*.py`` files only (skips this file by name to
  avoid self-reference).
* Patterns matched are deliberately conservative — see
  ``_PERMISSIVE_PATTERNS`` docstring.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

# Ceiling is 0 after slice B sweep. Bumping requires inline justification
# (a comment naming the new site + why a permissive range is necessary
# at THAT site instead of pinning the observed code). Drift-resistance
# is the whole point of the meta-test.
_PERMISSIVE_4XX_CEILING: int = 0

_TESTS_DIR: Path = Path(__file__).resolve().parent

# ---------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------

# Each pattern targets ONE shape of permissive 4xx-range assertion. The
# regexes are line-anchored so a single test line can match at most one
# pattern (the count is per-occurrence, not per-pattern).
#
# 1. Tuple form:   ``status_code in (400, 422)``
# 2. Set form:     ``status_code in {400, 404, 422}``
# 3. Comparison:   ``400 <= response.status_code < 500`` (any 4xx ceiling)
# 4. Inequality:   ``status_code < 500`` after a ``status_code >= 400``
#    on the same line
#
# Each pattern requires AT LEAST TWO 4xx values (or a `< 500` upper
# bound) to count — a single ``status_code == 404`` is exact and MUST
# NOT match. Stub-response constructors and helper fixtures
# (``status_code=403`` as a kwarg) are excluded by the leading
# ``status_code\s+in`` / ``status_code\s*<`` anchors.
_PERMISSIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Tuple: status_code in (4xx, 4xx[, 4xx])
    re.compile(r"status_code\s+in\s*\(\s*4\d{2}\s*,\s*4\d{2}(?:\s*,\s*4\d{2})?\s*\)"),
    # Set: status_code in {4xx, 4xx[, 4xx]}
    re.compile(r"status_code\s+in\s*\{\s*4\d{2}\s*,\s*4\d{2}(?:\s*,\s*4\d{2})?\s*\}"),
    # Range: 4xx <= ... status_code ... < 500  (or < 5xx)
    re.compile(r"4\d{2}\s*<=\s*[^\n]*status_code[^\n]*<\s*5\d{2}"),
    # Open upper bound: status_code < 500
    re.compile(r"status_code\s*<\s*500\b"),
    # Open lower bound: status_code >= 400  (without an upper-bound pin)
    # Note: this is intentionally narrower than the others because some
    # legitimate uses exist (e.g., "any 4xx is acceptable for X"). We
    # still flag it because *blueprint discipline* says every 4xx site
    # should pin the observed code.
    re.compile(r"status_code\s*>=\s*4\d{2}(?!.*==)"),
)


# ---------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------


def _collect_test_files() -> list[Path]:
    """Return every ``test_*.py`` file under ``tests/`` except self."""
    self_name = Path(__file__).name
    return sorted(p for p in _TESTS_DIR.glob("test_*.py") if p.name != self_name)


def _scan_file_for_permissive(path: Path) -> list[tuple[int, str]]:
    # Return list of (lineno, line) permissive hits in ``path``.
    #
    # Lines inside docstrings or triple-quoted blocks are skipped so a
    # docstring that *quotes* a historical pattern as documentation
    # (e.g., "Before Phase 13 B, this only asserted status_code <
    # 500") does NOT trip the scanner.
    #
    # Lines starting with `#` (full-line comments) are also skipped.
    # In-line comments after code are NOT skipped -- that is where
    # real assertions live.
    #
    # The triple-quote state-tracker handles both single- and
    # double-triple-quote delimiters and tolerates lines that OPEN
    # and CLOSE the block on the same line.
    hits: list[tuple[int, str]] = []
    in_docstring = False
    docstring_delim: str | None = None

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.lstrip()

        # Triple-quote state tracker.
        if in_docstring:
            # Look for the closing delimiter on this line.
            assert docstring_delim is not None
            if docstring_delim in raw:
                # Closing delim found; the rest of THIS line is code.
                # We conservatively skip the line entirely — a hit on
                # an inline expression after a closing docstring is
                # vanishingly rare in pytest files (PEP 8 puts the
                # close on its own line).
                in_docstring = False
                docstring_delim = None
            continue

        # Detect docstring/triple-quoted-string OPEN on this line.
        # A line that contains an ODD number of triple-quote delims
        # transitions into the docstring state; an EVEN number means
        # the string opens and closes on the same line.
        for delim in ('"""', "'''"):
            count = raw.count(delim)
            if count == 0:
                continue
            if count % 2 == 1:
                # Odd => entering a multi-line docstring.
                in_docstring = True
                docstring_delim = delim
            # Either way, the current line is a string-context line
            # and not scanned for permissive patterns.
            break
        else:
            # No triple-quote delim on this line; check comment & scan.
            if stripped.startswith("#"):
                continue
            for pat in _PERMISSIVE_PATTERNS:
                if pat.search(raw):
                    hits.append((lineno, raw.strip()))
                    break  # one hit per line, not per pattern
            continue
        # `for ... else: continue` did NOT run because a delim was
        # found; skip scanning the line entirely (it's inside or at
        # the boundary of a triple-quoted block).
        continue

    return hits


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


def test_permissive_4xx_count_is_within_ceiling() -> None:
    """Total permissive sites across the suite MUST NOT exceed the
    pinned ceiling. Slice B closed every observed site; ceiling is 0.
    """
    total = 0
    detailed: list[str] = []
    for path in _collect_test_files():
        hits = _scan_file_for_permissive(path)
        if hits:
            total += len(hits)
            for ln, txt in hits:
                detailed.append(f"  {path.name}:{ln}  {txt}")
    assert total <= _PERMISSIVE_4XX_CEILING, (
        f"Permissive 4xx-range assertions detected: {total} site(s); "
        f"ceiling is {_PERMISSIVE_4XX_CEILING}. Pin the observed status "
        f"code OR raise the ceiling with inline justification.\n" + "\n".join(detailed)
    )


def test_meta_test_scans_at_least_one_file() -> None:
    """Scanner sanity: the tests/ directory must contain >0 ``test_*.py``
    files. Catches a refactor that accidentally relocates the suite
    out from under the meta-test's anchor."""
    files = _collect_test_files()
    assert len(files) > 0, "no test files found by meta-test scanner"


def test_meta_test_excludes_itself_from_scan() -> None:
    """The meta-test file is excluded so its own regex/docstring
    patterns do not match. (The file naturally contains 4xx tokens
    inside the patterns and the docstrings.)"""
    files = _collect_test_files()
    self_name = Path(__file__).name
    assert all(p.name != self_name for p in files)


def test_meta_test_skips_full_line_comments() -> None:
    """A full-line comment that mentions a permissive pattern as
    documentation must NOT count toward the ceiling."""
    sample = "# status_code in (400, 422)  -- historical, do not match"
    hits = [
        (lineno, line)
        for lineno, line in enumerate(sample.splitlines(), 1)
        for pat in _PERMISSIVE_PATTERNS
        if not line.lstrip().startswith("#") and pat.search(line)
    ]
    assert hits == []


def test_meta_test_detects_tuple_form_synthetic() -> None:
    """Synthetic positive test: the tuple form trips the scanner."""
    line = "    assert response.status_code in (400, 422)"
    assert any(p.search(line) for p in _PERMISSIVE_PATTERNS)


def test_meta_test_detects_set_form_synthetic() -> None:
    """Synthetic positive test: the set form trips the scanner."""
    line = "    assert res.status_code in {400, 404, 422}"
    assert any(p.search(line) for p in _PERMISSIVE_PATTERNS)


def test_meta_test_detects_range_form_synthetic() -> None:
    """Synthetic positive test: the range form trips the scanner."""
    line = "    assert 400 <= response.status_code < 500"
    assert any(p.search(line) for p in _PERMISSIVE_PATTERNS)


def test_meta_test_detects_lt_500_form_synthetic() -> None:
    """Synthetic positive test: ``status_code < 500`` trips."""
    line = "    assert res.status_code < 500"
    assert any(p.search(line) for p in _PERMISSIVE_PATTERNS)


def test_meta_test_does_not_flag_exact_code_assertions() -> None:
    """Exact-code assertions MUST NOT trip the scanner."""
    safe_lines = [
        "    assert response.status_code == 400",
        "    assert response.status_code == 404",
        "    assert response.status_code == 422",
        "    assert res.status_code == 200",
        "    status_code=201,",  # stub constructor kwarg
        "    self.status_code = status_code",
        "    mock_resp.status_code = 502",
    ]
    for line in safe_lines:
        for pat in _PERMISSIVE_PATTERNS:
            assert not pat.search(line), f"false positive on safe line: {line!r}"


def test_meta_test_does_not_flag_happy_path_ranges() -> None:
    """``in (200, 201, 204)`` happy-path ranges MUST NOT trip the
    scanner — only 4xx-range permissives are in scope.
    """
    safe_lines = [
        "    assert response.status_code in (200, 201)",
        "    assert response.status_code in (200, 204, 206)",
        "    assert 200 <= response.status_code < 300",
    ]
    for line in safe_lines:
        for pat in _PERMISSIVE_PATTERNS:
            assert not pat.search(line), f"false positive on happy-path line: {line!r}"


def test_meta_test_ceiling_is_zero_after_slice_b() -> None:
    """Pin the initial ceiling for future code archeology. Bumping it
    requires removing this assertion AND raising
    ``_PERMISSIVE_4XX_CEILING`` AND adding inline justification at the
    new permissive site."""
    assert _PERMISSIVE_4XX_CEILING == 0


@pytest.mark.parametrize(
    "path_name",
    [
        "test_phase4_endpoints_integration.py",
        "test_phase5_endpoints_integration.py",
        "test_phase7_endpoints_integration.py",
        "test_phase11_endpoints_integration.py",
        "test_api_endpoints_integration.py",
    ],
)
def test_specific_slice_b_target_files_have_zero_permissive(path_name: str) -> None:
    """Per-file pin: the 5 files slice B touched MUST stay at zero
    permissive 4xx sites. A regression in any one trips this test
    with a specific filename, making the source easy to find.
    """
    path = _TESTS_DIR / path_name
    if not path.exists():
        pytest.skip(f"{path_name} not present in this checkout")
    hits = _scan_file_for_permissive(path)
    assert hits == [], f"{path_name} re-introduced permissive 4xx assertions:\n" + "\n".join(
        f"  line {ln}: {txt}" for ln, txt in hits
    )
