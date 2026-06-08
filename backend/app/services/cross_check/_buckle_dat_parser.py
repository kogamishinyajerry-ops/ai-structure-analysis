"""Shared `.dat` eigenvalue parser for CalculiX `*BUCKLE` runs.

FM-04a Phase 23 A extracted out of ``buckling_runner.py`` (Phase 22 A)
so the B31 beam-element runner (Phase 23 A) can reuse the same parser
without import gymnastics. CalculiX 2.21+ writes the header
``B U C K L I N G   F A C T O R``; older releases used
``E I G E N V A L U E``. Both spellings accepted.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import re
from pathlib import Path

from ...adapters.calculix.runner import CalculiXRunError

# Matches a row like ``     1   0.1727000E+04`` — leading optional
# whitespace, mode number, whitespace, signed scientific float.
_DAT_EIGENVALUE_RE = re.compile(
    r"^\s*\d+\s+([\-+]?\d+\.\d+(?:E[+\-]?\d+)?)",
    re.IGNORECASE,
)


def parse_lowest_buckling_eigenvalue(dat_path: Path) -> float:
    """Read CalculiX's ``.dat`` file and return the lowest eigenvalue.

    Returns the load multiplier of mode 1 (the first numeric row under
    the eigenvalue / buckling-factor header). The applied reference
    load multiplied by this value is the predicted buckling load.

    Raises:
        FileNotFoundError: if the .dat file is missing.
        CalculiXRunError: if the header is present but no eigenvalue
            row could be parsed (typical of a failed *BUCKLE step that
            still wrote a partial .dat).
    """
    if not dat_path.is_file():
        raise FileNotFoundError(
            f".dat file missing at {dat_path!s}; ccx may not have "
            f"completed the *BUCKLE step"
        )
    text = dat_path.read_text(encoding="utf-8", errors="replace")
    in_eigen_block = False
    for line in text.splitlines():
        stripped = line.strip().upper()
        if (
            "B U C K L I N G" in stripped
            or "E I G E N V A L U E" in stripped
        ):
            in_eigen_block = True
            continue
        if not in_eigen_block:
            continue
        if "MODE NO" in stripped or "FACTOR" in stripped:
            continue
        match = _DAT_EIGENVALUE_RE.match(line)
        if match:
            return float(match.group(1))
    raise CalculiXRunError(
        f"no eigenvalue found in {dat_path}; *BUCKLE step may have "
        f"failed without writing output",
        returncode=None,
        stderr_tail="",
        stdout_tail="",
    )


__all__ = ["parse_lowest_buckling_eigenvalue"]
