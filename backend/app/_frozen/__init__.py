"""Frozen modules — RFC-001 §6.1 Bucket B.

Submodules under this package are *frozen Sprint N* code: they remain
importable so live consumers don't break, but they are NOT part of the
MVP wedge described in `docs/RFC-001-strategic-pivot-and-mvp.md` §3.
Each submodule has its own README documenting its expiration policy
(M-N enable / M-N delete / never enable).

Do NOT add new code here. Edits should be limited to import-path
adjustments needed to keep the freeze compiling.
"""
