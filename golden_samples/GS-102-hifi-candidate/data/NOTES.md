# GS-102-hifi-candidate/data Notes

> Tier 1 engineering candidate; not signed validation; not benchmark agreement.

## Retained source files

This directory is a source fixture directory. Keep only:

- `model_00_0000.rad` - OpenRadioss starter deck.
- `model_00_0001.rad` - OpenRadioss engine deck.

The deck generator is `scripts/gen_gs102_hifi_deck.py`.

## Files that do not belong here

OpenRadioss runtime outputs are process artifacts and should not be kept under
`golden_samples/**`:

- `model_00A*`
- `model_00T*`
- `model_00_*.out`
- `model_00_*.rst`
- `starter.log`
- `engine.log`
- `*.tmp`

Run outputs should live under `project_state/runs/<case-id>/data`, with derived
metrics and visualizations under `project_state/graph_executor/<case-id>/`.

## Regeneration path

Regenerate the source decks with `scripts/gen_gs102_hifi_deck.py` if the hifi
fixture needs to be rebuilt. Do not use this directory as a solver working
directory; copy decks to `project_state/runs/<case-id>/data` before running
OpenRadioss.

## Claim boundary

This fixture supports engineering-candidate development only. Smoke tests,
candidate metrics, GIFs, and local solver outputs are not signed validation and
are not benchmark agreement.
