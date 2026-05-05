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

## 飞书周报（`06_generate_feishu`）摘要

- 脚本：`code/python/06_generate_feishu/generate_feishu_report.py`（详见根目录 **wkrpt** Skill 步骤 7）。
- 占位符登记：**`feishu_param_specs.py`**（`IMPLEMENTED_TEXT_PARAMS`、`TEXT_PARAM_SPECS`、插图关联）。
- **`-y` / `--yes`**：跳过「是否继续」；**`--strict`** / **`FEISHU_STRICT_PLACEHOLDERS=1`**：未登记或未成算的 `{占位符}` 直接失败。
- 模板内 **`{…dif}`**（参数名以 `dif` 结尾）：若值为数值，正文替换为 **「上升/下降」+ 两位小数**（**下降用绝对值、无负号**），**加粗**着色（**≥0 绿、&lt;0 红**；紧跟的 **`pp`** 一并着色）；**`rate_prin_od_dif` / `rate_cnt_od_dif`** 为 **≥0 红、&lt;0 绿**；非数值则普通替换。
- 由 **`m0_billing_grouped.json`** 计算 **ind0/ind1 月 7d 催回**、**IND1 占比**；由 **`m1_assignment_repayment.json` / `M2_class_all.json` / `M6_class_all.json`** 等计算 **`mth_mtdcolrate_*`**（与 assignment / M2 / M6 图口径一致）。
- 生成成功结束时在终端打印 **插入参数对照表** 与 **插图占位符说明**（stdout）。

## 最后更新

2026-05-03 — 新增本索引；与 `wkrpt` Skill、`sql`/`screens` README 同步维护。  
2026-05-03 — `sql/README` 补充 **`14_full_call` / `full_call.json`** 周粒度、`lag` 环比与维护说明。  
2026-05-04 — 补充 **`15_conect_rate` / `conect_rate.json`** 与 **`screen_call_type_weekly.py`**。  
2026-05-04 — 补充飞书 **`generate_feishu_report`** 的 `*dif` 着色与 **`m0_billing_grouped`** 派生参数说明。  
2026-05-06 — **`sql`**：新增 **`16_precall_task`**；**`screens`**：**`screen_precall_task.py`**；**`validate_data`**：**`precall_task.json`**；飞书模板插图 **`precall_task_trends.png`**（详见 **wkrpt** / 子目录 README）。  
2026-05-06 — **`sql`**：**`17_precall_afterkeep`**；**`screens`**：**`screen_precall_afterkeep.py`**；飞书：**`feishu_param_specs.py`**、**`*dif` 下降绝对值**、**`--strict`**、**`mth_mtdcolrate_*`**、成功结束时对照表打印。  
2026-04-30 — （历史）留案后外呼链路已与 **`validate_data`** 对齐注册。
