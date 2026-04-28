"""Layer-4 report CLI — RFC-001 §3 thin engineer-facing driver.

Exercises the full L1 → L4 stack from a terminal:
  1. Open a CalculiX ``.frd`` via ``CalculiXReader`` (Layer 1)
  2. Pull DISPLACEMENT + STRESS_TENSOR fields (Layer 2)
  3. Compute the templated quantities (Layer 3 derivations)
  4. Build (ReportSpec, EvidenceBundle) (Layer 4 schema)
  5. Validate against the chosen template (Layer 4 templates)
  6. Export DOCX with ADR-012 audit trail (Layer 4 exporter)

Three report kinds are supported, matching the three MVP templates:

  * ``static`` — equipment-foundation static-strength check
  * ``lifting-lug`` — lifting-lug strength assessment under hoist load
  * ``pressure-vessel`` — local stress assessment along an SCL
                         (requires ``--scl-nodes`` + ``--scl-distances``)

Exit codes (engineers script around these — treat as a contract):
  0  success — DOCX written
  2  argparse / input error (missing flag, malformed CSV, NaN, length
     mismatch between --scl-nodes and --scl-distances, etc.)
  3  domain refusal (ADR-012 violation, missing field, template-
     validation refusal, export refusal, etc.)
  4  unexpected internal error

Invocation::

    # As a console_script (after ``pip install -e .``):
    report-cli --frd path/to/result.frd --kind static --output report.docx

    # Or as a module (works from anywhere the package is importable):
    python -m app.services.report.cli --frd ... --kind static

The CLI is intentionally thin — every substantive piece of work lives
in the L1-L4 modules. This module's job is *plumbing*: turn argv
strings into typed parameters, surface refusals legibly, and write
the .docx. No engineering decisions hide here.
"""

from __future__ import annotations

import argparse
import math
import sys
import traceback
from pathlib import Path
from typing import NoReturn

# IMPORTANT — no top-level ``from app.X import Y`` imports.
#
# The Electron shell points engineers at ``report-cli --doctor`` when it
# can't spawn the report. If a broken in-tree submodule (e.g. a half-
# upgraded numpy that breaks ``app.adapters.calculix`` import, a circular
# import introduced by a refactor) makes ``import app.services.report.cli``
# itself fail at module load, ``--doctor`` never gets a chance to print
# the per-module diagnostic — the engineer sees a confusing
# ``ModuleNotFoundError`` from the launcher and has nothing actionable.
#
# Lazy-import the report-runtime stack inside ``main()`` and ``_produce()``
# so a broken submodule surfaces as a focused ``IMPORT FAILED`` line in
# the doctor output (Codex R1 HIGH, 2026-04-28). Repeated imports inside
# functions are O(1) lookups in ``sys.modules`` after the first call, so
# the cost is negligible compared to the runtime debuggability win.

__all__ = ["main", "build_parser"]


_REPORT_KINDS = ("static", "lifting-lug", "pressure-vessel", "ballistic")
# String keys only — argparse needs them at module load. We resolve to
# the ``UnitSystem`` enum inside ``main()`` after the lazy import, so
# this constant is safe even when ``app.core.types`` is broken.
_UNIT_SYSTEM_KEYS = ("si", "si-mm", "english", "unknown")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="report-cli",
        description=(
            "Generate a structural-analysis report (.docx) from a CalculiX .frd result file."
        ),
    )
    p.add_argument(
        "--frd",
        type=Path,
        default=None,
        help=(
            "Path to the CalculiX .frd result file. Required for a "
            "report run; ignored under --doctor."
        ),
    )
    p.add_argument(
        "--kind",
        choices=_REPORT_KINDS,
        default=None,
        help=(
            "Which report template to produce. 'pressure-vessel' "
            "additionally requires --scl-nodes and --scl-distances. "
            "'ballistic' uses --openradioss-root + --rootname instead "
            "of --frd. Required for a report run; ignored under --doctor."
        ),
    )
    # OpenRadioss reader inputs — used by 'ballistic' kind. Mutually
    # exclusive with --frd at flag-validation time below.
    p.add_argument(
        "--openradioss-root",
        type=Path,
        default=None,
        help=(
            "Path to the OpenRadioss run directory containing the "
            "<rootname>A### animation frames. Required for "
            "--kind=ballistic; mutually exclusive with --frd."
        ),
    )
    p.add_argument(
        "--rootname",
        default=None,
        help=(
            "OpenRadioss run rootname (the prefix of the .A### frames; "
            "e.g. 'BOULE1V5' for files BOULE1V5A001 / BOULE1V5A002). "
            "Required for --kind=ballistic."
        ),
    )
    p.add_argument(
        "--doctor",
        action="store_true",
        help=(
            "Print an installation-diagnostic and exit. Reports python "
            "version, key dependency versions (numpy / python-docx), and "
            "the report-cli console-script path so the engineer can "
            "confirm a working install. Exits 0 when healthy, 3 when "
            "any required component is missing or unimportable. Does not "
            "require --frd or --kind."
        ),
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("report.docx"),
        help="Output .docx path (default: ./report.docx).",
    )
    p.add_argument(
        "--unit-system",
        choices=sorted(_UNIT_SYSTEM_KEYS),
        default="si-mm",
        help="UnitSystem the .frd was produced in (default: si-mm).",
    )
    # Identity flags. Defaults are derived from the .frd stem so a
    # quick run doesn't need every ID specified explicitly.
    p.add_argument("--project-id", default=None)
    p.add_argument("--task-id", default=None)
    p.add_argument("--report-id", default=None)
    p.add_argument("--bundle-id", default=None)
    p.add_argument(
        "--step-id",
        type=int,
        default=None,
        help=("Optional solution-state ID. Defaults to the final state."),
    )
    p.add_argument(
        "--scl-nodes",
        default=None,
        help=(
            "Comma-separated node IDs along the SCL (inner→outer). "
            "Required for --kind=pressure-vessel."
        ),
    )
    p.add_argument(
        "--scl-distances",
        default=None,
        help=(
            "Comma-separated per-node distances along the SCL. "
            "Required for --kind=pressure-vessel. Must be uniformly "
            "spaced unless --resample is also given (in which case "
            "any strictly-monotonic series is accepted)."
        ),
    )
    p.add_argument(
        "--resample",
        type=int,
        default=None,
        metavar="N_POINTS",
        help=(
            "Linearly-resample the SCL tensor field onto N_POINTS "
            "uniformly-spaced points before linearization. Lets the "
            "engineer pass non-uniform CalculiX node spacing "
            "directly. Typical: --resample 21. Without this flag, "
            "non-uniform --scl-distances are rejected."
        ),
    )
    p.add_argument(
        "--validate-template",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Validate the produced report against the matching "
            "template before export (default: on). Disabling skips "
            "title-and-citation contract checks but does NOT skip "
            "ADR-012 cited-evidence checks in the exporter."
        ),
    )
    p.add_argument(
        "--figures",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Render result-figure PNGs (mesh outline, displacement, "
            "von Mises) alongside the DOCX and embed them as a Figures "
            "appendix. Default: on. Disable with --no-figures for "
            "headless / minimal-deps runs (e.g. CI without OS-Mesa)."
        ),
    )
    p.add_argument(
        "--figures-dir",
        type=Path,
        default=None,
        help=(
            "Directory for the rendered PNGs. Defaults to <output>.figs/ "
            "(sibling to the output .docx). Has no effect when "
            "--no-figures is set."
        ),
    )
    # W6a / ADR-019 — material data. The two flags are mutually
    # exclusive; argparse enforces that automatically. When neither
    # is supplied no § 材料属性 section is rendered (W5f-compatible).
    mat_group = p.add_mutually_exclusive_group()
    mat_group.add_argument(
        "--material",
        type=str,
        default=None,
        metavar="CODE_GRADE",
        help=(
            "Pick a built-in material by its standards-grade code "
            "(e.g. Q345B, SA-516-70). The DOCX gets a § 材料属性 "
            "section keyed to this material. Use --no-figures only "
            "if you have a reason to omit material data — without it "
            "the W6b allowable-stress / W6c PASS-FAIL chain is "
            "structurally impossible. List built-ins with "
            "--list-materials."
        ),
    )
    mat_group.add_argument(
        "--material-json",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Free-input material JSON file. Bypasses the built-in "
            "library; the resulting material is flagged "
            "[需工程师确认] in the DOCX (RFC-001 §2.4 rule 4). "
            "Schema: see ADR-019 §6 — bare entry or {'materials': [<entry>]} "
            "wrapper accepted."
        ),
    )
    p.add_argument(
        "--list-materials",
        action="store_true",
        help=(
            "Print the built-in material library code grades + standards "
            "and exit. Useful when scripting --material from another tool."
        ),
    )
    return p


def _resolve_identity_defaults(args: argparse.Namespace) -> None:
    """Auto-fill project_id/task_id/report_id/bundle_id from a stable
    stem when the engineer didn't supply them explicitly.

    Stem source depends on the input mode:
      * CalculiX (--frd path/to/run.frd)        → ``run`` (.frd basename)
      * OpenRadioss (--openradioss-root ...
        + --rootname BOULE1V5)                  → ``BOULE1V5``
      * neither (e.g. caller pre-populated all
        IDs)                                    → ``report`` fallback

    Codex R2 HIGH (PR #95): the earlier code unconditionally
    dereferenced ``args.frd.stem``, which crashes the ballistic CLI
    path with AttributeError because ``args.frd`` is None when the
    engineer passes ``--openradioss-root`` instead.
    """
    if args.frd is not None:
        stem = args.frd.stem or "report"
    elif args.rootname:
        stem = args.rootname
    else:
        stem = "report"
    if args.project_id is None:
        args.project_id = f"P-{stem}"
    if args.task_id is None:
        args.task_id = f"T-{stem}"
    if args.report_id is None:
        args.report_id = f"R-{stem}"
    if args.bundle_id is None:
        args.bundle_id = f"B-{stem}"


def _run_doctor() -> int:
    """Print an installation diagnostic and return an exit code.

    Healthy → 0. Any missing or unimportable required component → 3
    (matches the domain-refusal class in the module exit-code contract:
    a broken install can't produce reports).

    Stays inside this module deliberately — the Electron shell's spawn-
    failure hint says "run report-cli --doctor", and that hint should
    work without depending on app.adapters or app.models being fully
    importable. We import probes inline so a broken sub-module surfaces
    as a clear failure line, not a top-of-file ImportError that the
    engineer can't act on.
    """
    import importlib
    import shutil

    print("report-cli --doctor")
    print(f"  python: {sys.version.split()[0]}  ({sys.executable})")

    rc_path = shutil.which("report-cli")
    print(f"  report-cli on PATH: {rc_path or '<<not on PATH>>'}")
    print(f"  cli module: {Path(__file__).resolve()}")

    failed = False

    # Hard deps: anything required to produce a .docx. We split the
    # failure reporting between ``NOT INSTALLED`` (clean ImportError —
    # the wheel is missing) and ``BROKEN`` (any other Exception, e.g.
    # a transitive RuntimeError / AttributeError from a partial upgrade).
    # The contract per the module docstring is "missing or unimportable",
    # and an unimportable-but-installed package is still a doctor finding
    # the engineer needs to see — not a stack trace from a crashing probe.
    for module_name, label in (
        ("numpy", "numpy"),
        ("docx", "python-docx"),
    ):
        try:
            mod = importlib.import_module(module_name)
        except ImportError as exc:
            print(f"  {label}: NOT INSTALLED ({exc})")
            failed = True
            continue
        except Exception as exc:
            print(f"  {label}: BROKEN ({type(exc).__name__}: {exc})")
            failed = True
            continue
        version = getattr(mod, "__version__", "(no __version__)")
        print(f"  {label}: {version}")

    # In-tree imports — exercise the L1/L4 surfaces the report run
    # actually touches. Catch ImportError separately so a single broken
    # sub-module is a focused diagnostic line, not a confusing whole-
    # process traceback.
    for dotted in (
        "app.adapters.calculix",
        "app.services.report.draft",
        "app.services.report.exporter",
        "app.services.report.templates",
    ):
        try:
            importlib.import_module(dotted)
        except Exception as exc:  # ImportError + downstream init errors
            print(f"  {dotted}: IMPORT FAILED ({type(exc).__name__}: {exc})")
            failed = True
            continue
        print(f"  {dotted}: ok")

    if failed:
        print(
            "doctor: one or more required components are missing or broken.",
            file=sys.stderr,
        )
        return 3

    print("doctor: all required components are healthy.")
    return 0


def _input_error(msg: str) -> NoReturn:
    """Print an input-error message to stderr and exit with code 2.

    Centralizes the exit-code contract: argparse-style refusals are
    code 2 regardless of which call site raised them. ``SystemExit("...")``
    with a string argument exits with code 1, which would silently break
    the engineer-facing exit-code contract documented in the module
    docstring. Always go through this helper for argparse-level errors.
    """
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _parse_int_csv(label: str, raw: str) -> list[int]:
    """Parse a strict comma-separated list of integers.

    Empty fields (e.g. trailing comma, repeated commas) are an error,
    not silently dropped. Calls ``_input_error`` (exit 2) on any
    malformed input.
    """
    pieces = raw.split(",")
    out: list[int] = []
    for piece in pieces:
        stripped = piece.strip()
        if not stripped:
            _input_error(f"--{label}: empty field in comma-separated list (got {raw!r})")
        try:
            out.append(int(stripped))
        except ValueError as exc:
            _input_error(f"--{label}: expected comma-separated integers, got {raw!r} ({exc})")
    if not out:
        _input_error(f"--{label}: empty value")
    return out


def _parse_float_csv(label: str, raw: str) -> list[float]:
    """Parse a strict comma-separated list of finite floats.

    Empty fields are rejected. NaN and ±Inf are rejected — the
    pressure-vessel SCL contract requires finite, ordered, uniformly-
    spaced distances.
    """
    pieces = raw.split(",")
    out: list[float] = []
    for piece in pieces:
        stripped = piece.strip()
        if not stripped:
            _input_error(f"--{label}: empty field in comma-separated list (got {raw!r})")
        try:
            value = float(stripped)
        except ValueError as exc:
            _input_error(f"--{label}: expected comma-separated floats, got {raw!r} ({exc})")
        if not math.isfinite(value):
            _input_error(f"--{label}: non-finite value {stripped!r} (NaN/Inf not allowed)")
        out.append(value)
    if not out:
        _input_error(f"--{label}: empty value")
    return out


def _produce(
    args: argparse.Namespace,
    reader: "ReaderHandle",
) -> tuple[ReportSpec, EvidenceBundle, TemplateSpec]:
    """Dispatch to the matching producer + return the template that
    the report should validate against. ``reader`` is typed as a
    Layer-2 ``ReaderHandle`` because the ballistic kind takes an
    ``OpenRadiossReader`` (not a ``CalculiXReader``); the type is a
    forward ref under ``from __future__ import annotations`` so the
    lazy import inside this function still resolves it."""
    # Lazy imports — see the module-top comment. These names are bound
    # only here so a broken submodule surfaces in --doctor instead of
    # the import-time crash.
    from app.services.report.draft import (
        generate_ballistic_penetration_summary,
        generate_lifting_lug_summary,
        generate_pressure_vessel_local_stress_summary,
        generate_static_strength_summary,
    )
    from app.services.report.templates import (
        BALLISTIC_PENETRATION_SUMMARY,
        EQUIPMENT_FOUNDATION_STATIC,
        LIFTING_LUG,
        PRESSURE_VESSEL_LOCAL_STRESS,
    )

    # ``--resample`` is only meaningful for the pressure-vessel
    # template (it controls the SCL linearization grid). Silently
    # ignoring it for the other kinds would be a foot-gun: an
    # engineer who types ``--resample 21 --kind static`` would not
    # get any error and would never know their flag was discarded.
    if args.resample is not None and args.kind != "pressure-vessel":
        _input_error(
            f"--resample is only meaningful with --kind=pressure-vessel "
            f"(got --kind={args.kind!r}); remove --resample or change kind."
        )

    # ``--step-id`` is meaningful for static / lifting-lug / pressure-vessel
    # — they pick a single solution state. The ballistic generator
    # consumes the WHOLE time history; passing --step-id with --kind=ballistic
    # would be silently ignored, which is the foot-gun --resample dodged.
    if args.step_id is not None and args.kind == "ballistic":
        _input_error(
            "--step-id is not meaningful with --kind=ballistic — the "
            "ballistic generator iterates every solution state. "
            "Remove --step-id or pick a different --kind."
        )

    if args.kind == "ballistic":
        # Ballistic generator accepts no step_id (whole history).
        ballistic_kwargs = dict(
            project_id=args.project_id,
            task_id=args.task_id,
            report_id=args.report_id,
            bundle_id=args.bundle_id,
        )
        report, bundle = generate_ballistic_penetration_summary(
            reader, **ballistic_kwargs
        )
        return report, bundle, BALLISTIC_PENETRATION_SUMMARY

    common_kwargs = dict(
        project_id=args.project_id,
        task_id=args.task_id,
        report_id=args.report_id,
        bundle_id=args.bundle_id,
        step_id=args.step_id,
    )
    if args.kind == "static":
        report, bundle = generate_static_strength_summary(reader, **common_kwargs)
        return report, bundle, EQUIPMENT_FOUNDATION_STATIC
    if args.kind == "lifting-lug":
        report, bundle = generate_lifting_lug_summary(reader, **common_kwargs)
        return report, bundle, LIFTING_LUG
    # pressure-vessel
    if args.scl_nodes is None or args.scl_distances is None:
        _input_error("--kind=pressure-vessel requires --scl-nodes and --scl-distances.")
    nodes = _parse_int_csv("scl-nodes", args.scl_nodes)
    distances = _parse_float_csv("scl-distances", args.scl_distances)
    if len(nodes) != len(distances):
        _input_error(
            f"--scl-nodes ({len(nodes)} values) and --scl-distances "
            f"({len(distances)} values) must have equal length"
        )
    if args.resample is not None and args.resample < 2:
        _input_error(f"--resample must be >= 2; got {args.resample}")
    report, bundle = generate_pressure_vessel_local_stress_summary(
        reader,
        scl_node_ids=nodes,
        scl_distances=distances,
        resample_n_points=args.resample,
        **common_kwargs,
    )
    return report, bundle, PRESSURE_VESSEL_LOCAL_STRESS


def _run_list_materials() -> int:
    """Print the built-in material library and exit. One row per
    material on stdout in a stable, scriptable format:

        <code_grade>\\t<code_standard>\\t<sigma_y MPa>\\t<sigma_u MPa>\\t<citation>

    Tab-separated so engineers can pipe into ``awk`` / spreadsheet
    columns. Returns 0 on success and 3 if the bundled JSON is
    missing or malformed (matches --doctor's broken-install class).
    """
    from app.services.report.materials_lib import (
        MaterialLookupError,
        load_builtin_library,
    )

    try:
        lib = load_builtin_library()
    except MaterialLookupError as exc:
        print(f"error: built-in material library is broken: {exc}", file=sys.stderr)
        return 3
    print("# code_grade\tstandard\tsigma_y_MPa\tsigma_u_MPa\tcitation")
    for grade in sorted(lib.keys()):
        m = lib[grade]
        print(
            f"{m.code_grade}\t{m.code_standard}\t"
            f"{m.yield_strength:g}\t{m.ultimate_strength:g}\t"
            f"{m.source_citation}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Programmatic entry point.

    Returns an exit code on success and on caught domain refusals.
    Input-validation errors (argparse, malformed CSV, missing required
    SCL args, length mismatch) raise ``SystemExit(2)`` per the contract
    documented in the module docstring; ``argparse`` and ``_input_error``
    both honour exit code 2.

    Domain refusals (ADR-012 / template / export-error / producer
    ``ValueError``) are caught and reported on stderr with exit code 3.
    Unexpected exceptions surface as exit code 4 with a traceback.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.doctor:
        return _run_doctor()

    # --list-materials runs without --frd / --kind for the same reason
    # --doctor does (an introspection mode shouldn't require a real run).
    if args.list_materials:
        return _run_list_materials()

    # --frd / --openradioss-root and --kind are not argparse-required
    # so --doctor can run without them; enforce the report-run contract
    # here. Exactly one solver-input mode must be selected.
    if args.kind is None:
        _input_error("--kind is required (or pass --doctor for diagnostics).")

    using_openradioss = args.openradioss_root is not None or args.rootname is not None
    using_calculix = args.frd is not None
    if using_calculix and using_openradioss:
        _input_error(
            "--frd and --openradioss-root are mutually exclusive — pick "
            "exactly one solver input mode."
        )
    if args.kind == "ballistic":
        if args.figures:
            # The W5f figure renderer takes an FRDParseResult and walks
            # element connectivity directly — that path is CalculiX-only
            # right now (W7c-v2 will lift it to ReaderHandle once Mesh
            # Protocol exposes cell connectivity). The W7c animation
            # manifest is the supported visualization route for
            # ballistic runs.
            _input_error(
                "--figures is not yet wired for --kind=ballistic — the "
                "W5f renderer is CalculiX-FRD-only. Use the W7c "
                "animation manifest instead (or omit --figures)."
            )
        if not using_openradioss:
            _input_error(
                "--kind=ballistic requires --openradioss-root + --rootname."
            )
        if args.openradioss_root is None or args.rootname is None:
            _input_error(
                "--kind=ballistic requires BOTH --openradioss-root AND "
                "--rootname; got "
                f"--openradioss-root={args.openradioss_root!r} "
                f"--rootname={args.rootname!r}."
            )
        if not args.openradioss_root.is_dir():
            print(
                f"error: --openradioss-root path {args.openradioss_root} "
                "is not a directory",
                file=sys.stderr,
            )
            return 2
    else:
        if using_openradioss:
            _input_error(
                f"--openradioss-root / --rootname are only valid with "
                f"--kind=ballistic (got --kind={args.kind!r})."
            )
        if not using_calculix:
            _input_error(
                "--frd is required (or pass --doctor for diagnostics)."
            )
        if not args.frd.is_file():
            print(
                f"error: --frd path {args.frd} is not a file",
                file=sys.stderr,
            )
            return 2

    _resolve_identity_defaults(args)

    # W6a / Codex R1 PR #91 MEDIUM: validate --material / --material-json
    # BEFORE opening any I/O or running _produce(). A typo'd --material
    # should fail fast with a clear message, not after CalculiXReader
    # spins up and the report has been (re-)derived. Lookup is pure;
    # the audit-trail _detail line is emitted later when the stage
    # printer is wired up.
    material = None
    if args.material is not None or args.material_json is not None:
        from app.services.report.materials_lib import (
            MaterialLookupError,
            load_user_supplied_json,
            lookup_builtin,
        )
        try:
            if args.material is not None:
                material = lookup_builtin(args.material)
                if material is None:
                    print(
                        f"error: --material {args.material!r} is not in the "
                        f"built-in library. Run `report-cli --list-materials` "
                        f"to see available code grades.",
                        file=sys.stderr,
                    )
                    return 3
            else:
                material = load_user_supplied_json(args.material_json)
        except MaterialLookupError as exc:
            print(f"error: material refused: {exc}", file=sys.stderr)
            return 3

    # Lazy imports — see module-top comment. If any of these fail we
    # surface as exit 4 with an actionable hint pointing at --doctor;
    # the engineer ran a real report so there's no graceful degrade,
    # but the message is now self-explanatory.
    try:
        from app.adapters.calculix import CalculiXReader
        from app.core.types import UnitSystem
    except Exception as exc:
        print(
            f"internal error: cannot load report runtime ({type(exc).__name__}: {exc})\n"
            f"Hint: run `report-cli --doctor` to identify the broken module.",
            file=sys.stderr,
        )
        return 4

    unit_system = {
        "si": UnitSystem.SI,
        "si-mm": UnitSystem.SI_MM,
        "english": UnitSystem.ENGLISH,
        "unknown": UnitSystem.UNKNOWN,
    }[args.unit_system]

    # Per-stage progress lines go to stderr so the engineer running
    # the Electron wedge sees what the report-cli is doing instead of
    # a black-box "running…" → "done" jump. stdout stays reserved for
    # the final "wrote ..." summary so callers piping report-cli into
    # another tool still get exactly one stdout line per successful
    # run (the contract engineers script around).
    #
    # The Electron renderer routes both stdout and stderr into the
    # same log pane, so the engineer sees a flowing audit-trail.
    # Stage count is dynamic:
    #   1 read .frd
    #   2 produce report
    #   (optional) render figures — between 2 and validate
    #   (optional) validate template
    #   N export DOCX
    # The final stdout "wrote ..." line is not numbered — it's the
    # result, not a stage.
    total_stages = (
        2
        + (1 if args.figures else 0)
        + (1 if args.validate_template else 0)
        + 1  # export
    )

    def _stage(n: int, msg: str) -> None:
        print(f"[{n}/{total_stages}] {msg}", file=sys.stderr, flush=True)

    def _detail(msg: str) -> None:
        # ASCII '->' instead of U+2192. On Chinese-locale Windows (CP936)
        # Python's sys.stderr default-encodes the unicode arrow as
        # 0xA1FA, which the Electron shell then decodes as UTF-8 → the
        # log pane renders mojibake (��) for exactly the new audit-trail
        # lines. RFC-001 wedge audience is Chinese design institutes —
        # CP936 is the default environment, not an edge case.
        # (Codex R1 MEDIUM, 2026-04-28; verbatim fix.)
        print(f"      -> {msg}", file=sys.stderr, flush=True)

    if args.kind == "ballistic":
        _stage(
            1,
            f"reading OpenRadioss frames from {args.openradioss_root} "
            f"(rootname={args.rootname})",
        )
        try:
            from app.adapters.openradioss import OpenRadiossReader
        except Exception as exc:
            print(
                f"error: --kind=ballistic requires the optional "
                f"'openradioss' extra; install with `pip install "
                f"'.[openradioss]'`. Underlying ImportError: {exc}",
                file=sys.stderr,
            )
            return 3
        try:
            reader = OpenRadiossReader(
                root_dir=args.openradioss_root,
                rootname=args.rootname,
                unit_system=unit_system,
            )
        except Exception as exc:
            print(
                f"error: failed to open OpenRadioss run at "
                f"{args.openradioss_root} / {args.rootname}: {exc}",
                file=sys.stderr,
            )
            return 3
    else:
        _stage(1, f"reading CalculiX .frd: {args.frd}")
        try:
            reader = CalculiXReader(args.frd, unit_system=unit_system)
        except Exception as exc:
            print(f"error: failed to open {args.frd}: {exc}", file=sys.stderr)
            return 3
    _detail(f"opened (unit_system={args.unit_system})")

    _stage(2, f"producing report: kind={args.kind}")
    try:
        report, bundle, template = _produce(args, reader)
    except SystemExit:
        # _produce raises SystemExit for argparse-style input errors
        # we surfaced ourselves; re-raise to keep argparse's own flow.
        raise
    except (ValueError, KeyError) as exc:
        print(f"error: producer refused: {exc}", file=sys.stderr)
        return 3
    except Exception:  # pragma: no cover — defensive guard
        print(
            "internal error during report production:\n" + traceback.format_exc(),
            file=sys.stderr,
        )
        return 4
    _detail(f"{len(bundle.evidence_items)} evidence items, template={template.template_id}")

    next_stage = 3
    figures: dict[str, Path] = {}
    if args.figures:
        figs_dir = (
            args.figures_dir
            if args.figures_dir is not None
            else args.output.parent / f"{args.output.stem}.figs"
        )
        _stage(next_stage, f"rendering figures: {figs_dir}")
        next_stage += 1
        try:
            # Lazy-import viz so a missing pyvista/vtk surfaces here
            # (--doctor-friendly) instead of at module load. Re-parse
            # the .frd directly because the renderer needs raw element
            # connectivity, which the Layer-2 ReaderHandle Protocol
            # does NOT expose (and shouldn't — Mesh Protocol is
            # consumer-driven, viz consumers are rare).
            from app.parsers.frd_parser import FRDParser
            from app.viz.render import render_all

            parsed = FRDParser().parse(args.frd)
            figures = render_all(parsed, figs_dir)
            for name, path in figures.items():
                # Surface each figure path on stderr so the Electron
                # main process can pick it up and route to the renderer
                # gallery. The "figure:" prefix is the contract.
                print(f"figure: {path}", file=sys.stderr, flush=True)
            _detail(f"{len(figures)} figures: {', '.join(figures.keys())}")
        except Exception as exc:
            # Don't abort the report on a viz failure — the engineer
            # may not have a working OS-Mesa stack and still wants the
            # text report. Surface the failure on stderr (audit trail)
            # and continue without figures.
            print(
                f"warning: figure rendering failed ({type(exc).__name__}: {exc}); "
                f"continuing without figures. Pass --no-figures to suppress.",
                file=sys.stderr,
                flush=True,
            )
            figures = {}

    # W6a audit-trail: surface the chosen material on stderr so the
    # Electron log pane records it. Lookup itself happened pre-stage-1
    # (see fail-fast block above); here we only emit the detail line.
    if material is not None:
        if material.is_user_supplied:
            _detail(
                f"material: USER-SUPPLIED {material.code_grade} "
                f"({material.code_standard}) — flagged in DOCX"
            )
        else:
            _detail(
                f"material: {material.code_grade} ({material.code_standard}) "
                f"sigma_y={material.yield_strength:g} sigma_u={material.ultimate_strength:g}"
            )

    # Lazy-import the exporter + its refusal classes for the same
    # broken-submodule-survives-doctor reason as in _produce.
    from app.services.report.exporter import ExportError, export_docx
    from app.services.report.templates import TemplateValidationError
    if args.validate_template:
        _stage(next_stage, f"validating template: {template.template_id}")
        next_stage += 1

    _stage(next_stage, f"exporting DOCX: {args.output}")
    try:
        out = export_docx(
            report,
            bundle,
            output_path=args.output,
            template=template if args.validate_template else None,
            figures=figures or None,
            material=material,
        )
    except (ExportError, TemplateValidationError) as exc:
        print(f"error: export refused: {exc}", file=sys.stderr)
        return 3
    except Exception:  # pragma: no cover — defensive guard
        print(
            "internal error during DOCX export:\n" + traceback.format_exc(),
            file=sys.stderr,
        )
        return 4

    cited_count = len(bundle.evidence_items)
    print(
        f"wrote {out} (template={template.template_id}, "
        f"evidence_count={cited_count}, bundle_id={bundle.bundle_id})"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
