"""Parsers module — NL parsing exports.

Lazy export so the optional LLM client only loads when NLParser is touched.

RFC-001 §6.1 Bucket C: ResultParser / ParseResult removed (the .frd path
was a perpetual-empty stub and the .dat regex never matched real CalculiX
output). The replacement is the Layer-1 CalculiX adapter built in
W2 (RFC §4.5).
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "NLParser",
    "NLPResult",
]

_EXPORTS = {
    "NLParser": (".nl_parser", "NLParser"),
    "NLPResult": (".nl_parser", "NLPResult"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name, __name__)
    return getattr(module, attr_name)
