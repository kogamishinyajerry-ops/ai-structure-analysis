# HF3 Golden-Sample Registry Check

ENG-17 adds a read-only registry validator for `golden_samples/**`:

```bash
python scripts/gs_registry_check.py --root golden_samples
python scripts/gs_registry_check.py --root golden_samples --format json
```

The check classifies every `GS-*` directory into one explicit scope:

| Scope | Meaning | Signed golden standard? |
|---|---|---|
| `signed` | Traceable validation benchmark with `README.md`, `expected_results.json`, and `validation_source.yaml` | Yes |
| `smoke` | Adapter/runtime smoke fixture | No |
| `demo-unsigned` | End-to-end demo fixture without physics signature | No |
| `insufficient_evidence` | Existing case that cannot be used as a golden standard as configured | No |

Unknown scopes fail closed. This keeps GS-100 as an OpenRadioss adapter smoke
fixture, keeps `GS-101-demo-unsigned` out of signed ballistic validation, and
keeps GS-001/002/003 in `insufficient_evidence` until their FailurePattern
issues are actually resolved.

The validator does not modify `golden_samples/**`; it only reads local evidence
files and emits a pass/fail report for CI, review, or Linear proof comments.
