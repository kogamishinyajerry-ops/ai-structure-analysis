"""RFC-001 W8d — CLI entrypoint for the streaming VTU exporter.

Companion to ``viewport-cli`` (W8b). Where ``viewport-cli`` opens an
existing manifest, ``viewport-watch-cli`` PRODUCES a manifest live by
polling the OpenRadioss output directory and incrementally exporting
each ``A###`` frame as it appears.

Designed for a 3-process Electron orchestration:

  1. ``docker run openradioss:arm64 ...``     (engine writes A###.gz frames)
  2. ``viewport-watch-cli --root <bake>       (this CLI; writes manifest)
        --rootname model_00 --output <viz>``
  3. ``viewport-cli --live <viz>/             (W8b/W8c; reads manifest)
        viewport_manifest.json``

All three run concurrently; the manifest file is the contract between
them. When the engine finishes, no new frames appear, the watcher
idles out, and viewport-cli stays open with the complete timeline.

Refusal contract (mirrors ``export_run_streaming``):
  * exits 0 on clean idle-out / hard-timeout
  * exits 2 on argparse errors
  * exits 3 on VTUExportError (mid-run topology change, deletion-flag
    drift, unresolved gap, ambiguous frame, etc.)

This module is intentionally small — the heavy lifting is in
``app.viz.vtu_exporter.export_run_streaming``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.core.types import UnitSystem
from app.viz.vtu_exporter import VTUExportError, export_run_streaming


_USAGE = (
    "usage: viewport-watch-cli --root OPENRADIOSS_ROOT --rootname NAME "
    "--output OUTPUT_DIR [--max-idle-s SECONDS] "
    "[--poll-interval-s SECONDS] [--timeout-s SECONDS]"
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code.

    Required flags:
      --root      Directory containing ``<rootname>A###(.gz)`` frames.
      --rootname  OpenRadioss run rootname (e.g. ``model_00``).
      --output    Where to write ``viewport_manifest.json`` + states.

    Optional flags (defaults match ``export_run_streaming``):
      --max-idle-s        Exit cleanly after this many seconds of no
                          new frames. Default 30.
      --poll-interval-s   Seconds between dir scans. Default 1.0.
      --timeout-s         Hard wall-clock cap. Default: no cap.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    root: Path | None = None
    rootname: str | None = None
    output: Path | None = None
    max_idle_s = 30.0
    poll_interval_s = 1.0
    timeout_s: float | None = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--root":
            i += 1
            if i >= len(args):
                print(f"error: --root requires a value\n{_USAGE}", file=sys.stderr)
                return 2
            root = Path(args[i]).expanduser().resolve()
        elif a == "--rootname":
            i += 1
            if i >= len(args):
                print(
                    f"error: --rootname requires a value\n{_USAGE}",
                    file=sys.stderr,
                )
                return 2
            rootname = args[i]
        elif a == "--output":
            i += 1
            if i >= len(args):
                print(
                    f"error: --output requires a value\n{_USAGE}",
                    file=sys.stderr,
                )
                return 2
            output = Path(args[i]).expanduser().resolve()
        elif a == "--max-idle-s":
            i += 1
            if i >= len(args):
                print(
                    f"error: --max-idle-s requires a value\n{_USAGE}",
                    file=sys.stderr,
                )
                return 2
            try:
                max_idle_s = float(args[i])
            except ValueError:
                print(
                    f"error: --max-idle-s must be a number; got {args[i]!r}",
                    file=sys.stderr,
                )
                return 2
        elif a == "--poll-interval-s":
            i += 1
            if i >= len(args):
                print(
                    f"error: --poll-interval-s requires a value\n{_USAGE}",
                    file=sys.stderr,
                )
                return 2
            try:
                poll_interval_s = float(args[i])
            except ValueError:
                print(
                    f"error: --poll-interval-s must be a number; "
                    f"got {args[i]!r}",
                    file=sys.stderr,
                )
                return 2
        elif a == "--timeout-s":
            i += 1
            if i >= len(args):
                print(
                    f"error: --timeout-s requires a value\n{_USAGE}",
                    file=sys.stderr,
                )
                return 2
            try:
                timeout_s = float(args[i])
            except ValueError:
                print(
                    f"error: --timeout-s must be a number; got {args[i]!r}",
                    file=sys.stderr,
                )
                return 2
        else:
            print(f"error: unknown argument {a!r}\n{_USAGE}", file=sys.stderr)
            return 2
        i += 1

    if root is None or rootname is None or output is None:
        print(_USAGE, file=sys.stderr)
        return 2

    if not rootname:
        print(
            "error: --rootname must be non-empty",
            file=sys.stderr,
        )
        return 2

    try:
        manifest_path = export_run_streaming(
            openradioss_root=root,
            rootname=rootname,
            output_dir=output,
            unit_system=UnitSystem.SI_MM,
            max_idle_s=max_idle_s,
            poll_interval_s=poll_interval_s,
            timeout_s=timeout_s,
        )
    except VTUExportError as exc:
        print(f"viewport-watch: {exc}", file=sys.stderr)
        return 3

    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["main"]
