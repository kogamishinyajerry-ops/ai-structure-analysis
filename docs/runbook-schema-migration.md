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
   
## Verification
- Verify the newly added fields (Sprint, Model, Tokens Used, Tokens Budget, Branch, ADR Link, Start SHA) appear in both tasks and sessions databases.
