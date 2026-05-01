# `code/` 目录说明

周报自动化流水线中与 **SQL / Python / 大屏脚本** 相关的代码均在本目录下（路径相对项目根）。

## 子目录一览

| 目录 | 说明 | README |
|------|------|--------|
| **`sql/`** | Hive/SMART 查询脚本；`run_all.py` 按 `NN_xxx.sql` → `data/xxx.json` 落盘 | [`sql/README.md`](sql/README.md) |
| **`python/`** | 步骤编排：`01_execute_sql`、`025_check_rowcount`、`03_validate_data`、`055_analyze_template`、`06_generate_feishu` 等 | （按需在各子目录读源码注释） |
| **`screens/`** | `screen_*.py` 图表脚本；**推荐**用 `run_all_screens.py` 一键发现执行 | [`screens/README.md`](screens/README.md) |

## 与仓库其余路径的关系

- **`data/*.json`**：步骤 1 产出；默认 **`.gitignore`**，不提交。
- **`screenshots/*.png`**：步骤 5 产出；默认 **`.gitignore`**，不提交。
- **Skill / 流程说明**：项目根 `.claude/skills/wkrpt.md`（或 `.cursor/skills/wkrpt/SKILL.md`）。

## 最后更新

2026-05-03 — 新增本索引；与 `wkrpt` Skill、`sql`/`screens` README 同步维护。
