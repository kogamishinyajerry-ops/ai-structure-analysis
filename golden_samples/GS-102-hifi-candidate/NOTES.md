# GS-102-hifi-candidate Notes

> Tier 1 engineering candidate; not signed validation; not benchmark agreement.

## Purpose

This case keeps the hifi GS-102 OpenRadioss source fixture. The retained inputs
live under `data/`:

- `data/model_00_0000.rad` - starter deck.
- `data/model_00_0001.rad` - engine deck.

The deck generator is `scripts/gen_gs102_hifi_deck.py`.

## Runtime artifact policy

Do not keep solver runtime outputs in this `golden_samples/**` case directory.
`data/NOTES.md` lists the generated filename patterns that should be cleaned.

Runtime copies, logs, animation frames, metrics, manifests, GIFs, and reports
belong under:

- `project_state/runs/<case-id>/data`
- `project_state/graph_executor/<case-id>/...`
- `reports/gs102_<case-id>_candidate_run.md`

## Regeneration

Regenerate source decks with:

```sh
python3 scripts/gen_gs102_hifi_deck.py
```

The transient candidate pipeline defaults to the refined fixture, so hifi runs
must pass this source directory explicitly:

```sh
python3 scripts/gs102_transient_candidate_pipeline.py \
  --case-id <case-id> \
  --source-case-dir golden_samples/GS-102-hifi-candidate/data
```

## Claim boundary

This case is a Tier 1 engineering-candidate fixture only. Local solver output,
candidate metrics, GIFs, and reports are not signed validation and are not
benchmark agreement.

## Open governance gap

This case does not yet carry a dedicated `expected_results.json`. Add one only
through an explicit evidence/governance slice; do not infer stronger claims
from the retained decks.
