#!/usr/bin/env python3
"""
path_manager.py — Dynamic project root and Obsidian Vault discovery.
"""

import os
from pathlib import Path
from typing import Optional

def get_repo_root() -> Path:
    """Find the repository root by searching upward for .git folder or file."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    # Fallback to current working directory if .git is not found
    return Path.cwd()

def get_obsidian_vault() -> Path:
    """
    Get the Obsidian Vault path.
    Priority:
    1. Environment variable ANTIGRAVITY_OBSIDIAN_VAULT
    2. Hardcoded fallback
    """
    env_path = os.environ.get("ANTIGRAVITY_OBSIDIAN_VAULT")
    if env_path:
        return Path(env_path)
    
    # Standard fallback
    return Path("/Users/Zhuanz/Documents/Obsidian Vault")

def get_project_vault_dir() -> Path:
    """Get the specific directory for this project within the Obsidian Vault."""
    vault = get_obsidian_vault()
    # We use the repo name or a project identifier
    repo_name = get_repo_root().name
    # Mapping certain folder names to recognizable project IDs if needed
    if "AI StructureAnalysis" in repo_name:
        return vault / "AI_Structure_Analysis"
    return vault / repo_name

if __name__ == "__main__":
    print(f"Repo Root:      {get_repo_root()}")
    print(f"Obsidian Vault: {get_obsidian_vault()}")
    print(f"Project Vault:  {get_project_vault_dir()}")
