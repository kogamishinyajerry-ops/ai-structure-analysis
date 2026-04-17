# Well Harness Architecture

本项目现在具备一套面向结构分析场景的 `well_harness` 自动化编排层，用来复用 `cfd-harness-unified` 的核心思想，同时保持当前 FEA 项目的领域边界不变。

## 闭环

```text
Golden Sample / Notion TaskSpec
        ->
well_harness.task_runner
        ->
executor (replay / calculix)
        ->
FRD parser + report generator
        ->
reference verification
        ->
project_state persistence
        ->
deterministic Notion / GitHub sync payload
```

## 组成

- `backend/app/well_harness/knowledge_store.py`
  - 从 `golden_samples/` 解析 `TaskSpec`、输入文件、结果文件和参考值。
- `backend/app/well_harness/executors.py`
  - `ReplayExecutor` 用现有 FRD 做回放。
  - `CalculixExecutor` 在本机有 `ccx` 时支持实际求解。
- `backend/app/well_harness/task_runner.py`
  - 主编排器，负责执行、解析、报告、验证、handoff、状态持久化。
- `backend/app/well_harness/project_state.py`
  - 统一把 `input_summary / output_summary / artifacts / control_plane_sync / handoff` 固化到 `project_state/`。
- `backend/app/well_harness/control_plane.py`
  - 输出稳定的 Notion / GitHub payload，而不是在仓库内直接做线上写操作。

## 输出约定

每次运行都会在 `project_state/runs/<case_id>/<run_id>/` 下生成：

- `input_summary.json`
- `output_summary.json`
- `artifacts.json`
- `control_plane_sync.json`
- `handoff.md`

这套结构对应了 Dispatcher 体系里最关键的三件事：

1. 输入摘要可追溯
2. 输出摘要可审计
3. 决策和后续动作可外部同步

## 运行方式

```bash
python3 run_well_harness.py GS-001 GS-002 GS-003
```

或者安装项目后使用：

```bash
run-well-harness GS-001 GS-002 GS-003
```
