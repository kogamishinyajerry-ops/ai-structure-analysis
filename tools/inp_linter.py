"""Static lint for CalculiX ``.inp`` decks — P1-06 Gate-Solve front door.

The goal is to catch trivially-detectable defects *before* spawning ``ccx``,
so the solver node can short-circuit with a precise ``fault_class`` instead of
spending a retry budget on a 30s container run that ends with a one-line
``*ERROR in input``.

Scope (intentionally tight):
  * Keyword spelling for the dozen most-common CalculiX keywords.
  * Required blocks: ``*NODE``, ``*ELEMENT``, ``*MATERIAL``, ``*STEP`` ↔ ``*END STEP``.
  * Referential integrity: materials / elsets / nsets referenced vs. defined.
  * Duplicate node / element IDs.
  * Known element-type catalog (rejects typos like ``C3B8`` or ``S44``).

Out of scope (explicit non-goals for P1-06):
  * Physical validity (geometry, load magnitude, mesh quality — lives in Gate-Mesh + ADR-004 fault_classes).
  * Semantic analysis-type compatibility (that's ``*STEP``-level — deferred).
  * Performance heuristics (element-count warnings, etc.).

Wired into ADR-004: findings with severity=ERROR map to ``FaultClass.SOLVER_SYNTAX``
so the Reviewer sees a coherent fault_class chain whether the defect is caught
pre-solve (here) or post-solve (``calculix_driver.classify_solver_failure``).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from schemas.sim_state import FaultClass

# ---------------------------------------------------------------------------
# Keyword catalog — the set CalculiX documents as valid top-level keywords.
# Derived from CalculiX 2.21 User's Manual §7. Truncated to members we expect
# to see in P1/P2 decks; adding a new one here is a 1-line change.
# ---------------------------------------------------------------------------
KNOWN_KEYWORDS: frozenset[str] = frozenset(
    {
        "HEADING",
        "NODE",
        "ELEMENT",
        "NSET",
        "ELSET",
        "MATERIAL",
        "ELASTIC",
        "PLASTIC",
        "DENSITY",
        "EXPANSION",
        "CONDUCTIVITY",
        "SPECIFIC HEAT",
        "SOLID SECTION",
        "SHELL SECTION",
        "BEAM SECTION",
        "MEMBRANE SECTION",
        "BOUNDARY",
        "INITIAL CONDITIONS",
        "AMPLITUDE",
        "STEP",
        "STATIC",
        "DYNAMIC",
        "FREQUENCY",
        "BUCKLE",
        "HEAT TRANSFER",
        "MODAL DYNAMIC",
        "CLOAD",
        "DLOAD",
        "TEMPERATURE",
        "NODE FILE",
        "EL FILE",
        "NODE PRINT",
        "EL PRINT",
        "CONTACT PAIR",
        "SURFACE",
        "SURFACE INTERACTION",
        "TIE",
        "EQUATION",
        "INCLUDE",
        "END STEP",
    }
)

# Common typos observed in the wild or produced by LLM agents. Value is the
# canonical spelling. Anything not in this table but also not in KNOWN_KEYWORDS
# gets an "unknown keyword" lint.
KNOWN_TYPOS: dict[str, str] = {
    "CLAOD": "CLOAD",
    "BONDARY": "BOUNDARY",
    "BOUNDRY": "BOUNDARY",
    "MATRIAL": "MATERIAL",
    "MATERAIL": "MATERIAL",
    "ELSTIC": "ELASTIC",
    "SOILD SECTION": "SOLID SECTION",
    "HEADNG": "HEADING",
    "ENDSTEP": "END STEP",
    "END_STEP": "END STEP",
    "STPE": "STEP",
    "DLAOD": "DLOAD",
}

# Element types CalculiX 2.21 accepts. Used to flag things like "C3B8" typos.
KNOWN_ELEMENT_TYPES: frozenset[str] = frozenset(
    {
        "C3D4", "C3D6", "C3D8", "C3D8I", "C3D8R", "C3D10", "C3D10T",
        "C3D15", "C3D20", "C3D20R",
        "S3", "S4", "S4R", "S6", "S8", "S8R",
        "B31", "B31R", "B32", "B32R",
        "T2D2", "T3D2", "T3D3",
        "CPS3", "CPS4", "CPS6", "CPS8",
        "CPE3", "CPE4", "CPE6", "CPE8",
        "CAX3", "CAX4", "CAX6", "CAX8",
        "DC3D4", "DC3D6", "DC3D8", "DC3D10", "DC3D15", "DC3D20",
        "SPRING1", "SPRING2", "SPRINGA",
        "DASHPOTA",
        "GAPUNI",
        "MASS",
    }
)


@dataclass
class LintFinding:
    """A single defect identified in the deck."""

    severity: str  # "error" or "warning"
    code: str  # stable machine-readable ID like "E-UNKNOWN-KEYWORD"
    line: int | None
    message: str
    fault_class_hint: FaultClass | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # asdict converts StrEnum to the enum object form in some Python
        # versions; normalize to string so json.dumps works.
        if self.fault_class_hint is not None:
            d["fault_class_hint"] = self.fault_class_hint.value
        return d


@dataclass
class LintReport:
    """Aggregated lint output for one deck."""

    deck_path: str
    findings: list[LintFinding] = field(default_factory=list)

    @property
    def errors(self) -> list[LintFinding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[LintFinding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "deck_path": self.deck_path,
            "ok": self.ok,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_KEYWORD_RE = re.compile(r"^\*\s*([A-Z][A-Z\s]*?)\s*(?:,|$)", re.IGNORECASE)


def _iter_keyword_lines(lines: list[str]) -> Iterable[tuple[int, str, str]]:
    """Yield ``(lineno, keyword_upper, full_line)`` for each ``*KEYWORD`` line.

    Comments (``**``) and continuation data lines are skipped. ``lineno`` is
    1-based so it matches editor + error-message conventions.
    """
    for i, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("**"):
            continue
        if not stripped.startswith("*"):
            continue
        m = _KEYWORD_RE.match(stripped)
        if not m:
            continue
        kw = m.group(1).strip().upper()
        # Collapse internal whitespace: "END   STEP" -> "END STEP"
        kw = re.sub(r"\s+", " ", kw)
        yield i, kw, stripped


def _parse_attrs(line: str) -> dict[str, str]:
    """Parse ``*KEYWORD, FOO=bar, BAZ=qux`` into a dict (keys upper, values raw)."""
    parts = [p.strip() for p in line.split(",")[1:]]
    out: dict[str, str] = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip().upper()] = v.strip()
        else:
            out[p.upper()] = ""
    return out


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_keywords(lines: list[str], report: LintReport) -> None:
    """Every ``*KEYWORD`` must be known or a documented typo."""
    for lineno, kw, _full in _iter_keyword_lines(lines):
        if kw in KNOWN_KEYWORDS:
            continue
        if kw in KNOWN_TYPOS:
            canonical = KNOWN_TYPOS[kw]
            report.findings.append(
                LintFinding(
                    severity="error",
                    code="E-TYPO-KEYWORD",
                    line=lineno,
                    message=f"*{kw} is a common misspelling of *{canonical}.",
                    fault_class_hint=FaultClass.SOLVER_SYNTAX,
                )
            )
            continue
        report.findings.append(
            LintFinding(
                severity="error",
                code="E-UNKNOWN-KEYWORD",
                line=lineno,
                message=f"*{kw} is not a recognized CalculiX 2.21 keyword.",
                fault_class_hint=FaultClass.SOLVER_SYNTAX,
            )
        )


def _check_required_blocks(lines: list[str], report: LintReport) -> None:
    """Minimum blocks for a solvable static deck."""
    seen: set[str] = {kw for _, kw, _ in _iter_keyword_lines(lines)}

    for required in ("NODE", "ELEMENT", "MATERIAL", "STEP"):
        if required not in seen:
            report.findings.append(
                LintFinding(
                    severity="error",
                    code=f"E-MISSING-{required}",
                    line=None,
                    message=f"Deck has no *{required} block.",
                    fault_class_hint=FaultClass.SOLVER_SYNTAX,
                )
            )

    step_count = sum(1 for _, kw, _ in _iter_keyword_lines(lines) if kw == "STEP")
    end_step_count = sum(1 for _, kw, _ in _iter_keyword_lines(lines) if kw == "END STEP")
    if step_count != end_step_count:
        report.findings.append(
            LintFinding(
                severity="error",
                code="E-UNBALANCED-STEP",
                line=None,
                message=(
                    f"*STEP count ({step_count}) does not match *END STEP count "
                    f"({end_step_count})."
                ),
                fault_class_hint=FaultClass.SOLVER_SYNTAX,
            )
        )


def _check_element_types(lines: list[str], report: LintReport) -> None:
    for lineno, kw, full in _iter_keyword_lines(lines):
        if kw != "ELEMENT":
            continue
        attrs = _parse_attrs(full)
        etype = attrs.get("TYPE")
        if not etype:
            report.findings.append(
                LintFinding(
                    severity="error",
                    code="E-ELEMENT-NO-TYPE",
                    line=lineno,
                    message="*ELEMENT block is missing TYPE= attribute.",
                    fault_class_hint=FaultClass.SOLVER_SYNTAX,
                )
            )
            continue
        if etype.upper() not in KNOWN_ELEMENT_TYPES:
            report.findings.append(
                LintFinding(
                    severity="error",
                    code="E-UNKNOWN-ELEMENT-TYPE",
                    line=lineno,
                    message=(
                        f"TYPE={etype} is not a recognized CalculiX element type. "
                        "(Known types include C3D8, C3D8I, C3D20R, S4, B31, T3D2.)"
                    ),
                    fault_class_hint=FaultClass.SOLVER_SYNTAX,
                )
            )


def _collect_defined_names(lines: list[str]) -> tuple[set[str], set[str], set[str]]:
    """Return ``(materials, elsets, nsets)`` defined by the deck."""
    materials: set[str] = set()
    elsets: set[str] = set()
    nsets: set[str] = set()
    for _, kw, full in _iter_keyword_lines(lines):
        attrs = _parse_attrs(full)
        if kw == "MATERIAL" and "NAME" in attrs:
            materials.add(attrs["NAME"].upper())
        if kw == "ELEMENT" and "ELSET" in attrs:
            elsets.add(attrs["ELSET"].upper())
        if kw == "ELSET" and "ELSET" in attrs:
            elsets.add(attrs["ELSET"].upper())
        if kw == "NSET" and "NSET" in attrs:
            nsets.add(attrs["NSET"].upper())
        if kw == "NODE" and "NSET" in attrs:
            nsets.add(attrs["NSET"].upper())
    return materials, elsets, nsets


def _check_section_references(lines: list[str], report: LintReport) -> None:
    materials, elsets, _ = _collect_defined_names(lines)
    section_kws = {"SOLID SECTION", "SHELL SECTION", "BEAM SECTION", "MEMBRANE SECTION"}
    for lineno, kw, full in _iter_keyword_lines(lines):
        if kw not in section_kws:
            continue
        attrs = _parse_attrs(full)
        elset = attrs.get("ELSET", "").upper()
        material = attrs.get("MATERIAL", "").upper()
        if elset and elset not in elsets:
            report.findings.append(
                LintFinding(
                    severity="error",
                    code="E-UNDEFINED-ELSET",
                    line=lineno,
                    message=f"*{kw} references ELSET={attrs['ELSET']} but no such elset is defined.",
                    fault_class_hint=FaultClass.SOLVER_SYNTAX,
                )
            )
        if material and material not in materials:
            report.findings.append(
                LintFinding(
                    severity="error",
                    code="E-UNDEFINED-MATERIAL",
                    line=lineno,
                    message=(
                        f"*{kw} references MATERIAL={attrs['MATERIAL']} but no such material is defined."
                    ),
                    fault_class_hint=FaultClass.SOLVER_SYNTAX,
                )
            )


def _check_duplicates(lines: list[str], report: LintReport) -> None:
    """Duplicate node and element IDs trip silent ccx overwrites — find them early."""
    current_block: str | None = None  # "NODE" or "ELEMENT" or None
    node_ids: dict[int, int] = {}  # id -> first-seen line
    elem_ids: dict[int, int] = {}
    for lineno, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("**"):
            continue
        if stripped.startswith("*"):
            for _, kw, _full in _iter_keyword_lines([raw]):
                if kw == "NODE":
                    current_block = "NODE"
                elif kw == "ELEMENT":
                    current_block = "ELEMENT"
                else:
                    current_block = None
            continue
        if current_block not in ("NODE", "ELEMENT"):
            continue
        # Data line — first token is the ID.
        first_tok = stripped.split(",", 1)[0].strip()
        try:
            ident = int(first_tok)
        except ValueError:
            continue
        bucket = node_ids if current_block == "NODE" else elem_ids
        if ident in bucket:
            report.findings.append(
                LintFinding(
                    severity="error",
                    code=f"E-DUPLICATE-{current_block}-ID",
                    line=lineno,
                    message=(
                        f"{current_block.lower()} id {ident} redeclared "
                        f"(first seen on line {bucket[ident]})."
                    ),
                    fault_class_hint=FaultClass.SOLVER_SYNTAX,
                )
            )
        else:
            bucket[ident] = lineno


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lint_inp(deck_path: str | Path) -> LintReport:
    """Static-analyze a CalculiX ``.inp`` deck and return a ``LintReport``.

    Deterministic and pure — does not invoke ``ccx``. Safe to call from any
    node in the graph, including Architect before handing off to Geometry.
    """
    path = Path(deck_path)
    if not path.exists():
        raise FileNotFoundError(f"Deck not found: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    report = LintReport(deck_path=str(path))

    _check_keywords(lines, report)
    _check_required_blocks(lines, report)
    _check_element_types(lines, report)
    _check_section_references(lines, report)
    _check_duplicates(lines, report)

    # Stable ordering: errors first, then warnings, then by line number.
    report.findings.sort(
        key=lambda f: (
            0 if f.severity == "error" else 1,
            f.line if f.line is not None else -1,
            f.code,
        )
    )
    return report
