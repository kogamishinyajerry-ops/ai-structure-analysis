"""CalculiX Layer-1 adapter — subprocess runner (FM-04a Phase 18 A).

Spawns the real ``ccx`` (CalculiX) binary as a subprocess for a given
case directory + jobname. Captures stdout/stderr, enforces a bounded
timeout, refuses signed-registry paths (defense in depth), and returns
a structured ``CalculiXRunResult`` carrying paths to the produced
``.frd`` (results) and ``.dat`` (printable) artifacts when they exist.

Layer split (RFC-001 §4.5):
* This runner is responsible for SUBPROCESS INVOCATION only. It does
  not parse the resulting ``.frd`` — that responsibility lives in
  :class:`app.adapters.calculix.reader.CalculiXReader` and Layer-3
  ``app.domain.stress_derivatives`` for derived quantities.
* This runner does not generate the input ``.inp`` file either —
  that lives in :mod:`app.adapters.calculix.inp_writer` (Phase 18 A
  minimal-hex template) and (Phase 18 C) the mesh+materials pipeline.

Tier 2 posture (per Phase 18 blueprint §0): this is the first real
solver invocation in the harness. The runner does NOT mock anything;
when invoked it really executes ``ccx``. Tests that exercise this path
carry the ``@pytest.mark.requires_solver`` marker so CI without ccx
installed can still run the default sweep.

Defense in depth:
* HF1.7a — signed-registry case-id pattern is refused by the runner
  before any subprocess launch. The Phase 17-and-earlier hard-stop
  on writing inside signed-registry cases composes with the runner's
  case_dir validation.
* Bounded timeout — every ``run()`` call carries a wall-clock cap;
  long-running solver jobs are killed and a ``CalculiXRunError`` is
  raised rather than wedging the calling process indefinitely.
* stdout/stderr captured to files — the calling process never reads
  unbounded solver chatter; the test can tail the captured files for
  diagnostics when a run fails.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CCX_BINARY = "ccx"
"""Default solver binary name. Resolved via PATH unless overridden by
the constructor or environment. Local dev box typically has
``/opt/homebrew/bin/ccx`` (Homebrew CalculiX 2.23+)."""

DEFAULT_TIMEOUT_SEC = 300.0
"""Default wall-clock cap for a single ccx run. Small linear-static
models converge in <5 seconds; the 5-minute default is generous for
larger cohort cases while still bounded enough that a stuck job
doesn't wedge CI."""

_SIGNED_REGISTRY_PATTERN = re.compile(r"^GS-\d{3}$")
"""HF1.7a defense — refuses ``case_dir.name`` matching the signed-
registry shape ``^GS-\\d{3}$``. The Tier 2 transition (Phase 18) keeps
this guard intact: signed-registry cases remain protected even as the
broader Tier 1 posture is relaxed."""

_DEFAULT_STDOUT_TAIL_BYTES = 8192
_DEFAULT_STDERR_TAIL_BYTES = 8192


class CalculiXRunError(RuntimeError):
    """Raised when a ``ccx`` subprocess fails to produce results.

    Carries diagnostics so callers (notably the AI advisor + UI error
    surface) can present an actionable error without re-reading the
    full stdout/stderr.
    """

    def __init__(
        self,
        message: str,
        *,
        returncode: int | None,
        stderr_tail: str,
        stdout_tail: str,
    ) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr_tail = stderr_tail
        self.stdout_tail = stdout_tail


@dataclass(frozen=True)
class CalculiXRunResult:
    """Outcome of a single ``ccx`` subprocess execution.

    Attributes:
        returncode: ccx's process exit code (0 on success).
        stdout_path: absolute path to the captured stdout log.
        stderr_path: absolute path to the captured stderr log.
        frd_path: absolute path to the ``.frd`` result file when
            produced, else ``None``. Most successful linear-static
            runs produce one; failed runs may omit it.
        dat_path: absolute path to the ``.dat`` printable file when
            produced, else ``None``.
        runtime_sec: wall-clock seconds the subprocess took.
    """

    returncode: int
    stdout_path: Path
    stderr_path: Path
    frd_path: Path | None
    dat_path: Path | None
    runtime_sec: float


class CalculiXRunner:
    """Spawn ``ccx`` subprocess for a given case directory + jobname.

    Usage:

        runner = CalculiXRunner()  # uses `ccx` from PATH
        result = runner.run(case_dir=Path("/tmp/case1"), jobname="model")
        if result.frd_path:
            reader = CalculiXReader(result.frd_path, unit_system=...)
            # ... Layer-3 derivations from reader.get_field(...)

    Args:
        ccx_binary: path or name of the ccx executable. Defaults to
            ``"ccx"`` (resolved via PATH).
        timeout_sec: wall-clock cap; subprocess is killed beyond this.
    """

    def __init__(
        self,
        ccx_binary: str | Path = DEFAULT_CCX_BINARY,
        *,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        self._binary = str(ccx_binary)
        self._timeout_sec = float(timeout_sec)

    def run(self, case_dir: Path, jobname: str) -> CalculiXRunResult:
        """Execute ``ccx -i <jobname>`` inside ``case_dir``.

        The case directory MUST already contain ``<jobname>.inp`` (the
        solver input). Produces ``<jobname>.frd`` + ``<jobname>.dat`` +
        ``<jobname>.cvg`` + ``<jobname>.sta`` adjacent on success.

        Raises:
            CalculiXRunError: if ``case_dir`` is a signed-registry
                case (HF1.7a defense), if the input ``.inp`` is
                missing, if the subprocess times out, or if ccx
                exits non-zero.
        """
        case_dir = Path(case_dir).resolve()
        if _SIGNED_REGISTRY_PATTERN.fullmatch(case_dir.name):
            raise CalculiXRunError(
                f"refused to run ccx inside signed-registry case "
                f"{case_dir.name!r} (HF1.7a defense)",
                returncode=None,
                stderr_tail="",
                stdout_tail="",
            )
        if not case_dir.is_dir():
            raise CalculiXRunError(
                f"case_dir {case_dir!s} is not a directory",
                returncode=None,
                stderr_tail="",
                stdout_tail="",
            )
        inp_path = case_dir / f"{jobname}.inp"
        if not inp_path.is_file():
            raise CalculiXRunError(
                f"input file {inp_path!s} is missing",
                returncode=None,
                stderr_tail="",
                stdout_tail="",
            )

        stdout_path = case_dir / f"{jobname}.stdout.log"
        stderr_path = case_dir / f"{jobname}.stderr.log"

        start = time.monotonic()
        try:
            with (
                stdout_path.open("w", encoding="utf-8") as stdout_f,
                stderr_path.open("w", encoding="utf-8") as stderr_f,
            ):
                completed = subprocess.run(  # noqa: S603 - controlled args
                    [self._binary, "-i", jobname],
                    cwd=str(case_dir),
                    stdout=stdout_f,
                    stderr=stderr_f,
                    timeout=self._timeout_sec,
                    check=False,
                )
        except subprocess.TimeoutExpired as exc:
            runtime = time.monotonic() - start
            stdout_tail = _safe_tail(stdout_path, _DEFAULT_STDOUT_TAIL_BYTES)
            stderr_tail = _safe_tail(stderr_path, _DEFAULT_STDERR_TAIL_BYTES)
            raise CalculiXRunError(
                f"ccx subprocess timed out after {runtime:.2f}s "
                f"(cap {self._timeout_sec}s) for jobname={jobname!r}",
                returncode=None,
                stderr_tail=stderr_tail,
                stdout_tail=stdout_tail,
            ) from exc
        except FileNotFoundError as exc:
            raise CalculiXRunError(
                f"ccx binary not found at {self._binary!r}; install "
                f"CalculiX or override the binary path",
                returncode=None,
                stderr_tail="",
                stdout_tail="",
            ) from exc

        runtime = time.monotonic() - start

        frd_path: Path | None = case_dir / f"{jobname}.frd"
        if not frd_path.is_file():
            frd_path = None
        dat_path: Path | None = case_dir / f"{jobname}.dat"
        if not dat_path.is_file():
            dat_path = None

        if completed.returncode != 0:
            stdout_tail = _safe_tail(stdout_path, _DEFAULT_STDOUT_TAIL_BYTES)
            stderr_tail = _safe_tail(stderr_path, _DEFAULT_STDERR_TAIL_BYTES)
            raise CalculiXRunError(
                f"ccx exited with returncode {completed.returncode} "
                f"for jobname={jobname!r}",
                returncode=completed.returncode,
                stderr_tail=stderr_tail,
                stdout_tail=stdout_tail,
            )

        return CalculiXRunResult(
            returncode=completed.returncode,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            frd_path=frd_path,
            dat_path=dat_path,
            runtime_sec=runtime,
        )


def _safe_tail(path: Path, max_bytes: int) -> str:
    """Return the last ``max_bytes`` of ``path`` as utf-8 text.

    Used for ``CalculiXRunError`` diagnostics; never raises on read
    failure (returns empty string instead). Encoding errors are
    replaced rather than raised.
    """
    try:
        size = path.stat().st_size
        offset = max(0, size - max_bytes)
        with path.open("rb") as f:
            f.seek(offset)
            data = f.read()
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""
