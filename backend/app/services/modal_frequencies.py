"""Modal eigenfrequency extraction — FM-04a Phase 19 C.

CalculiX writes modal-eigenvalue results to the `.frd` and the `.dat`
file. The `.dat` line ``E I G E N V A L U E   N U M B E R ... PRECISION``
header is followed by mode rows with ``mode_number  eigenvalue (rad²/s²)
angular_freq (rad/s)  frequency (Hz)  period (s)``. We parse the .dat
because the .frd modal blocks use a less convenient binary-ish layout
across ccx versions; .dat is plain text and stable.

The parser is intentionally permissive about whitespace + tolerant of
ccx version differences (some ccx builds add trailing PRECISION
information; some don't). It returns a list of frequencies in Hz,
ascending.
"""

from __future__ import annotations

import re
from pathlib import Path

_EIGENVALUE_HEADER_RE = re.compile(
    # ccx 2.21 emits "E I G E N V A L U E   O U T P U T"; older builds
    # use "E I G E N V A L U E   N U M B E R". Match the common
    # prefix to stay robust across versions.
    r"E\s*I\s*G\s*E\s*N\s*V\s*A\s*L\s*U\s*E",
    re.IGNORECASE,
)
# Captures: mode_number, eigenvalue (rad²/s²), ang_freq (rad/s),
# frequency (Hz). The trailing fields (period etc.) are optional.
_EIGENVALUE_ROW_RE = re.compile(
    r"^\s*(\d+)\s+"           # mode number
    r"([-+]?\d+\.?\d*[eE]?[-+]?\d*)\s+"   # eigenvalue
    r"([-+]?\d+\.?\d*[eE]?[-+]?\d*)\s+"   # angular frequency rad/s
    r"([-+]?\d+\.?\d*[eE]?[-+]?\d*)"      # frequency Hz
)


def extract_eigen_frequencies(dat_path: Path) -> list[float]:
    """Return the list of eigenfrequencies (Hz) parsed from a ccx
    `.dat` file, in ascending order.

    Args:
        dat_path: path to the ``.dat`` printable produced by a modal
            ccx run.

    Returns:
        A list of frequencies in Hz; empty when no eigenvalue block
        is found (e.g., the run failed before computing modes).

    Raises:
        FileNotFoundError: if the .dat file doesn't exist.
    """
    if not dat_path.is_file():
        raise FileNotFoundError(f".dat file {dat_path!s} not found")
    text = dat_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    frequencies: list[float] = []
    in_block = False
    for line in lines:
        if _EIGENVALUE_HEADER_RE.search(line):
            in_block = True
            continue
        if not in_block:
            continue
        stripped = line.strip()
        if not stripped:
            # Blank lines between header and rows + between rows are
            # permitted; skip without ending the block.
            continue
        match = _EIGENVALUE_ROW_RE.match(line)
        if match is None:
            # Non-blank, non-row line: either the MODE NO column-
            # header (skip-through) or end of block. Distinguish by
            # whether we've already started collecting rows.
            if frequencies:
                break
            # Pre-row column header (e.g., "MODE NO EIGENVALUE ...") —
            # skip and keep scanning.
            continue
        frequencies.append(float(match.group(4)))

    return sorted(frequencies)


__all__ = ["extract_eigen_frequencies"]
