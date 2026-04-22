#!/usr/bin/env python3
"""
obsidian_sync.py — Dynamic synchronization of project state to Obsidian Vault.
Specialized for worktree-robust path handling.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from path_manager import get_repo_root, get_project_vault_dir

def ensure_vault_structure(project_dir: Path):
    """Ensure the standard governance structure exists in Obsidian."""
    subdirs = ["01_开发日志", "02_架构决策记录", "03_RVM归档", "05_Opus审查记录"]
    project_dir.mkdir(parents=True, exist_ok=True)
    for sd in subdirs:
        (project_dir / sd).mkdir(exist_ok=True)

def update_bootstrap_protocol(project_dir: Path, repo_root: Path):
    """Update the Agent Bootstrap Protocol with the current worktree path."""
    protocol_path = project_dir / "04_Agent启动协议.md"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Template or existing content
    if protocol_path.exists():
        content = protocol_path.read_text(encoding="utf-8")
    else:
        content = f"""# 🤖 Agent 启动协议 — {repo_root.name}

> **此文件由于治理脚本自动维护，确保 Antigravity 能够跨 Worktree 恢复上下文。**

---

## ⚡ 30秒上下文恢复

### 关键路径 (动态更新)

```
项目根目录:  {repo_root}/
```

---

## 🏗️ 核心架构约束

1. **路径鲁棒性**: 此项目支持 Git Worktree。始终以系统 Metadata 提供的路径为准。

---
"""

    # Update the project root path
    pattern = r"项目根目录:\s+.*"
    replacement = f"项目根目录:  {repo_root}/"
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
    else:
        # Append if not found
        content += f"\n项目根目录:  {repo_root}/\n"

    # Add/Update the Worktree Awareness rule
    rule_section = "## ⚠️ Worktree 自动适配规则"
    rule_content = f"""
{rule_section}

> [!IMPORTANT]
> **当前活动路径**: `{repo_root}`
> **更新时间**: {now_str}
> 
> 如果此路径与你当前所在的目录不一致，说明用户切换了 Worktree。
> **请务必忽略所有历史日志中的绝对路径，并以当前的 `{repo_root}` 为基准进行路径重基（Re-base）。**
"""
    
    if rule_section in content:
        # Replace existing rule section
        content = re.sub(rf"{rule_section}.*?(?=\n##|\Z)", rule_content, content, flags=re.DOTALL)
    else:
        content += rule_content

    protocol_path.write_text(content, encoding="utf-8")
    print(f"  ✅ Updated Agent Bootstrap Protocol at {protocol_path}")

def main():
    repo_root = get_repo_root()
    project_vault = get_project_vault_dir()
    
    print(f"\n🔄 Running Obsidian Worktree Sync...")
    print(f"  📍 Current Repo Root: {repo_root}")
    print(f"  📂 Obsidian Project Dir: {project_vault}")
    
    ensure_vault_structure(project_vault)
    update_bootstrap_protocol(project_vault, repo_root)
    
    print(f"\n✅ Sync Complete. Antigravity is now anchored to this worktree.\n")

if __name__ == "__main__":
    main()
