# Antigravity Worktree Survival Rules

This file provides persistent instructions for AI coding agents (Antigravity/Gemini) to ensure robustness across different disk locations and Git worktrees.

## 核心规则 (Core Rules)

1. **路径动态化 (Path Dynamism)**:
   - 始终优先使用系统 Metadata 提供的当前工作空间根目录。
   - 严禁在脚本或文档中写入包含 `/Users/Zhuanz/...` 的绝对路径。
   - 在读取任何历史日志或知识条目（KIs）时，如果其中包含的绝对路径与当前路径不符，必须自动进行“重基（Re-base）”。

2. **环境变量优先**:
   - 外部依赖（如 Obsidian Vault）应尽可能通过 `PathManager` 或环境变量获取，而不是硬编码。

3. **管控协议锚点**:
   - 在开始任何新阶段任务前，运行 `python3 governance/obsidian_sync.py` 来锚定当前 Worktree 到 Obsidian 协议中。

## 故障排除

如果 Antigravity 报错找不到文件，请检查：
- 当前 Metadata 中的 URI。
- 是否正在读取来自另一个 Worktree 的过时记忆。
- 是否可以通过 `path_manager.py` 动态定位正确的文件。
