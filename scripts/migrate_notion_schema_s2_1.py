import argparse
import os
import sys
from typing import Any, Dict

import httpx

NOTION_API_BASE_URL = "https://api.notion.com/v1"
DEFAULT_NOTION_VERSION = "2026-03-11"

NEW_PROPERTIES = {
    "Sprint": {"select": {"options": [{"name": "S2.1", "color": "blue"}]}},
    "Model": {"select": {"options": [{"name": "Claude Sonnet 4.6", "color": "orange"}, {"name": "Gemini 3.1 Pro", "color": "purple"}, {"name": "Gemini 3 Flash", "color": "yellow"}]}},
    "Tokens Used": {"number": {"format": "number"}},
    "Tokens Budget": {"number": {"format": "number"}},
    "Branch": {"rich_text": {}},
    "ADR Link": {"url": {}},
    "Start SHA": {"rich_text": {}}
}

def migrate_database(database_id: str, token: str, dry_run: bool) -> None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": DEFAULT_NOTION_VERSION,
        "Content-Type": "application/json",
    }
    
    with httpx.Client(base_url=NOTION_API_BASE_URL, headers=headers, timeout=30.0) as client:
        response = client.get(f"/databases/{database_id}")
        response.raise_for_status()
        db_info = response.json()
        existing_props = db_info.get("properties", {})
        
        props_to_add = {}
        for prop_name, prop_schema in NEW_PROPERTIES.items():
            if prop_name not in existing_props:
                props_to_add[prop_name] = prop_schema
        
        if not props_to_add:
            print(f"Database {database_id} is already up to date.")
            return

        print(f"Database {database_id} needs the following properties:")
        for k in props_to_add:
            print(f"  - {k}")
            
        if dry_run:
            print("[DRY-RUN] Skipping actual update.")
            return
            
        update_payload = {"properties": props_to_add}
        update_resp = client.patch(f"/databases/{database_id}", json=update_payload)
        update_resp.raise_for_status()
        print(f"Database {database_id} updated successfully.")

def main():
    parser = argparse.ArgumentParser(description="Migrate Notion schema for S2.1")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be added without actually updating.")
    parser.add_argument("--tasks-db", required=True, help="Task database ID")
    parser.add_argument("--sessions-db", required=True, help="Session database ID")
    
    args = parser.parse_args()
    
    token = os.environ.get("NOTION_API_KEY")
    if not token:
        print("Error: NOTION_API_KEY environment variable is required.", file=sys.stderr)
        sys.exit(1)
        
    print("Migrating Tasks Database...")
    migrate_database(args.tasks_db, token, args.dry_run)
    
    print("\nMigrating Sessions Database...")
    migrate_database(args.sessions_db, token, args.dry_run)

if __name__ == "__main__":
    main()
