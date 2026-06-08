"""Regression for round-2 audit B1: the PDF-export route raised NameError.

`backend/app/api/routes/report.py::export_report_pdf` builds the download filename with
``datetime.now().strftime(...)`` (the last line before returning the StreamingResponse), but
the module never imported ``datetime`` — so every successful export built the PDF buffer one
line earlier, then raised ``NameError: name 'datetime' is not defined``, which the handler's
``except`` turned into an opaque HTTP 500. PDF export was non-functional since repo init.

A full happy-path route test is disproportionate here (it needs a real ``.frd`` under
``gs_root``, the report generator, the PDF service, and a working ``get_db`` —
``settings.gs_root`` is a read-only property). The defect is a *missing import*, so the
proportionate, reliable guard is to assert the
module actually binds ``datetime`` to the stdlib type and that the exact filename expression the
handler uses resolves. If the import is removed again, ``report.datetime`` disappears (no other
reference in the module) and this fails.
"""

from __future__ import annotations

import datetime as _stdlib_datetime

import app.api.routes.report as report_module


def test_report_module_binds_stdlib_datetime() -> None:
    assert hasattr(report_module, "datetime"), (
        "report.py must import `datetime`; export_report_pdf references datetime.now()"
    )
    assert report_module.datetime is _stdlib_datetime.datetime


def test_export_filename_expression_resolves() -> None:
    # The exact expression from export_report_pdf — proves datetime.now().strftime works
    # against the symbol the module actually exposes (not a test-local import).
    case_id = "demo-candidate"
    filename = f"Report_{case_id}_{report_module.datetime.now().strftime('%Y%m%d')}.pdf"
    assert filename.startswith(f"Report_{case_id}_")
    assert filename.endswith(".pdf")
    # YYYYMMDD stamp is 8 digits
    stamp = filename[len(f"Report_{case_id}_") : -len(".pdf")]
    assert stamp.isdigit() and len(stamp) == 8
