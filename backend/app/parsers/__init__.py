"""Parsers module - results and NL parsing exports.

Use lazy exports so result-only workflows do not import optional LLM clients
unless the NL parser is explicitly requested.
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "ResultParser",
    "ParseResult",
    "NLParser",
    "NLPResult",
]

_EXPORTS = {
    "ResultParser": (".result_parser", "ResultParser"),
    "ParseResult": (".result_parser", "ParseResult"),
    "NLParser": (".nl_parser", "NLParser"),
    "NLPResult": (".nl_parser", "NLPResult"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name, __name__)
    return getattr(module, attr_name)
