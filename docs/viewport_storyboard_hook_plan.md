# W8e Screenshot-on-Frame Storyboard Hook Plan

ENG-20 is a planning slice. It does not claim that report-cli already embeds
ballistic viewport screenshots in DOCX. It identifies the existing hook points
and the implementation contract for the next code slice.

## Current Code Evidence

| Surface | Current capability | Gap for W8e |
|---|---|---|
| `backend/app/viz/vtu_exporter.py` | Exports OpenRadioss `A###` frames into `viewport_manifest.json` plus `states/*.vtu`; streaming mode appends states as frames arrive. | No PNG paths are written into the manifest. |
| `backend/app/viz/viewport_native.py` | `render_snapshots(manifest_path, output_dir, field=...)` renders one PNG per manifest state using off-screen PyVista. CLI supports `--snapshots`. | Snapshot output is a side command, not integrated into report-cli. |
| `backend/app/services/report/cli.py` | Ballistic `--viewport-out` emits VTU + manifest before DOCX export. Static `--figures` renders and embeds FRD figures. | Ballistic path rejects `--figures`; it does not run viewport snapshots or pass them to DOCX export. |
| `backend/app/services/report/exporter.py` | `_render_figures_appendix()` embeds a caller-provided ordered `dict[str, Path]` of PNGs into the DOCX. | Captions are generic figure names; no ballistic storyboard metadata is passed. |
| `backend/tests/test_viewport_native.py` | Covers snapshot refusal paths and GS-101 demo snapshot PNG generation when OpenRadioss/Docker prerequisites exist. | Does not assert report-cli snapshot orchestration or DOCX embedding. |
| `tests/test_report_cli_figures.py` | Covers static figure rendering, figure path stderr events, and DOCX embedded image count. | Does not cover ballistic storyboard frames. |

## Target User Workflow

One command should produce a report packet with a viewport manifest, selected
frame PNGs, and a DOCX appendix:

```bash
report-cli \
  --kind ballistic \
  --openradioss-root /path/to/bake \
  --rootname model_00 \
  --output /path/to/report.docx \
  --viewport-out /path/to/report.viewport \
  --storyboard-out /path/to/report.storyboard
```

`--storyboard-out` is the proposed explicit flag. It avoids overloading
`--figures`, which currently means static CalculiX FRD figures and is rejected
for `--kind=ballistic`.

## Hook Contract

1. `report-cli` keeps the current order: read result, produce report, emit
   viewport manifest, then export DOCX.
2. When `--storyboard-out` is set for `--kind=ballistic`, the CLI calls
   `app.viz.viewport_native.render_snapshots()` after `export_run()` returns a
   manifest path.
3. The snapshot caller selects frames through a deterministic policy:
   - default: first, middle, final frame;
   - if erosion data exists: include the first frame where alive count drops;
   - de-duplicate by `step_id` while preserving chronological order.
4. Snapshot artifact names are stable and sortable:
   - `storyboard/frame_001_step_001_t_0.000ms.png`
   - `storyboard/frame_002_step_006_t_1.500ms.png`
   - `storyboard/frame_003_step_011_t_3.000ms.png`
5. The CLI passes an ordered `dict[str, Path]` into `export_docx()`:
   - key format: `Ballistic storyboard - step <step_id>, t=<time_ms> ms`;
   - value: absolute PNG path.
6. `export_docx()` can initially reuse `_render_figures_appendix()`; a later
   polish slice may split this into `_render_storyboard_appendix()` only if the
   caption/table layout needs more metadata.
7. The viewport manifest should optionally record each selected frame's
   `png_path` and `frame_index` only after the PNG exists and is non-empty. If
   manifest mutation is added, it must be atomic like `vtu_exporter.write_manifest()`.

## Artifact Layout

For output `/runs/gs101/report.docx`:

```text
/runs/gs101/report.docx
/runs/gs101/report.viewport/viewport_manifest.json
/runs/gs101/report.viewport/states/state_001.vtu
/runs/gs101/report.storyboard/frame_001_step_001_t_0.000ms.png
/runs/gs101/report.storyboard/frame_002_step_006_t_1.500ms.png
/runs/gs101/report.storyboard/frame_003_step_011_t_3.000ms.png
```

Large solver decks and baked frames remain runtime artifacts. The repo should
only gain source code, tests, and small synthetic fixtures.

## Failure Behavior

The existing viewport-export behavior is allowed to warn and continue with a
DOCX-only report. W8e should preserve that posture:

| Failure | CLI behavior |
|---|---|
| `--storyboard-out` omitted | No snapshot stage; current behavior unchanged. |
| `--storyboard-out` used without `--viewport-out` | Exit 2 with an argument error; snapshots need a manifest source. |
| `render_snapshots()` raises `ViewportError` | Warn on stderr and continue with DOCX-only output. |
| Snapshot PNG missing or zero bytes after render | Warn and omit that frame from DOCX; if all selected frames fail, emit no storyboard appendix. |
| DOCX export refuses for evidence/template reasons | Preserve current refusal; storyboard artifacts may still exist as side artifacts. |

## Verification Plan

Unit tests:

- Add a pure frame-selection helper test using a synthetic manifest payload.
- Assert first/middle/final selection, erosion-drop insertion, de-duplication,
  and chronological ordering.

CLI tests:

- Add parser tests for `--storyboard-out`.
- Assert `--storyboard-out` without `--viewport-out` returns exit code 2.
- Monkeypatch `export_run()` and `render_snapshots()` so ballistic report-cli
  can be tested without Docker/OpenRadioss/PyVista.
- Assert the generated figure dict keys are ordered storyboard captions and
  paths point to the rendered PNGs.

DOCX tests:

- Reuse python-docx introspection from `tests/test_report_cli_figures.py`.
- Assert a ballistic DOCX contains one inline image per selected storyboard
  frame when the monkeypatched snapshots exist.
- Assert zero-byte or missing PNGs are not embedded.

Integration tests:

- Keep the existing GS-101 demo snapshot test optional because it depends on
  Docker, `openradioss:arm64`, PyVista, and local graphics support.
- When prerequisites exist, run:

```bash
.venv/bin/python -m pytest backend/tests/test_viewport_native.py::test_snapshots_emit_one_png_per_state -q
```

Acceptance checks:

- PNG existence: every selected storyboard image exists and has non-zero size.
- DOCX embedding: `len(Document(report.docx).inline_shapes)` increases by the
  number of selected storyboard frames.
- Honest wording: report or UI text says `demo-unsigned` or
  `validation-candidate` unless ENG-22 is approved and a signed benchmark exists.

## Non-Goals

- No signed GS-101 claim.
- No OpenRadioss solver-truth carve-out.
- No changes to `golden_samples/**`.
- No solver/deck/runtime artifact checked into the repo.
- No live viewport GUI capture; W8e uses off-screen snapshot rendering from
  the exported VTU manifest.
