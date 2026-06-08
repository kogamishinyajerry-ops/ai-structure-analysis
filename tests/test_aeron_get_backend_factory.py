"""Tests for aeron.drivers.get_backend — the ADR-028 D4 P2 solver-dispatch factory.

The factory is the single place that maps a ``SimPlan`` solver name to a concrete
``FEABackend``. Its honesty contract: CalculiX is built; any other *known* backend
is rejected with ``NotImplementedError`` (never a silent CalculiX fallback that would
solve an unsupported physics as if it were the requested one); an *unknown* name fails
at enum normalization with ``ValueError`` before any backend is constructed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aeron.drivers import get_backend
from aeron.protocols import FEABackend
from schemas.sim_plan import SolverBackend


def _kwargs(tmp_path: Path) -> dict[str, object]:
    # The CalculiX constructor only stores these paths; it does not touch the
    # filesystem until prepare_case(), so non-existent paths are fine here.
    return {"work_root": tmp_path, "mesh_input": tmp_path / "model.inp"}


def test_calculix_enum_returns_fea_backend(tmp_path):
    backend = get_backend(SolverBackend.CALCULIX, **_kwargs(tmp_path))
    # FEABackend is @runtime_checkable, so structural conformance is assertable.
    assert isinstance(backend, FEABackend)
    assert backend.solver_name == "calculix"


def test_calculix_string_name_is_accepted(tmp_path):
    # The factory normalizes a plain wire string through SolverBackend(name).
    backend = get_backend("calculix", **_kwargs(tmp_path))
    assert isinstance(backend, FEABackend)


def test_fenics_is_not_implemented(tmp_path):
    with pytest.raises(NotImplementedError) as exc:
        get_backend(SolverBackend.FENICS, **_kwargs(tmp_path))
    assert "fenics" in str(exc.value).lower()


def test_openradioss_is_not_implemented(tmp_path):
    # OpenRadioss has a real backend class but is deliberately NOT dispatched here
    # (ballistic path deferred to ADR-028 P5; its constructor takes decks, not .inp).
    with pytest.raises(NotImplementedError):
        get_backend(SolverBackend.OPENRADIOSS, **_kwargs(tmp_path))


def test_unknown_name_raises_value_error(tmp_path):
    # Normalization rejects an unknown name BEFORE constructing anything.
    with pytest.raises(ValueError):
        get_backend("foobar", **_kwargs(tmp_path))
