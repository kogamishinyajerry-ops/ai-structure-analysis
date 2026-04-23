# Runbook: Schema Migration S2.1

This runbook outlines the steps to apply the Notion schema migration for the S2.1 sprint updates, as detailed in ADR-010.

## Prerequisites
- Valid `NOTION_API_KEY` with schema-editing permissions for the target databases.
- The Task and Session Database IDs.
- Python 3.9+ with `httpx` installed.

## Execution

1. **Dry-Run (Mandatory)**
   Always perform a dry-run first to review the planned additions:
   ```bash
   python scripts/migrate_notion_schema_s2_1.py --dry-run --tasks-db <YOUR_TASK_DB_ID> --sessions-db <YOUR_SESSION_DB_ID>
   ```
   *Expected output: A list of properties that will be added to the databases.*

2. **Apply Migration**
   Execute the migration by omitting the `--dry-run` flag:
   ```bash
   python scripts/migrate_notion_schema_s2_1.py --tasks-db <YOUR_TASK_DB_ID> --sessions-db <YOUR_SESSION_DB_ID>
   ```

3. **Idempotency**
   The script is idempotent. Running it multiple times will not duplicate properties or fail if properties already exist.
   
## GitHub Actions 触发流程

The schema migration script and `well_harness` execution are orchestrated via GitHub Actions `.github/workflows/well_harness.yml`.

1. **Pull Request Trigger (`pull_request`)**
   - Automatically executes `well_harness` run against the `case_id` parsed from the PR title (e.g. `[AI-FEA-S2.1-03]`).
   - Syncs the local results back to Notion via `notion_sync.py`, linking the run to the PR.

2. **Approval Dispatch (`repository_dispatch: notion_approval`)**
   - Once a Notion Task reaches a human approval verdict, Kogami triggers the dispatch payload.
   - The workflow will automatically `squash merge` the PR if `Accept` or `close` the PR if `Reject`.

3. **Post-Merge Mainline Sync (`push: main`)**
   - Automatically dry-runs the S2.1 schema migration upon ADR modifications to validate contract alignment.
   - Triggers an automated smoke verification run (`GS-001`) to assert pipeline integrity.

## Verification
- Verify the newly added fields (Sprint, Model, Tokens Used, Tokens Budget, Branch, ADR Link, Start SHA) appear in both tasks and sessions databases.
- Confirm that PRs correctly trigger the `well_harness` runs and drop summary comments.
