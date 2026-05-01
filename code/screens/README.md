# 图表生成模块（`code/screens/`）

本目录包含周报所需的 **`screen_*.py`** 画图脚本及编排入口。**推荐**在项目根执行 **`python code/screens/run_all_screens.py`**：自动发现全部 `screen_*.py`，子进程隔离运行（单脚本超时 300s）。

```powershell
# 项目根
python code/screens/run_all_screens.py           # 全部
python code/screens/run_all_screens.py --list    # 仅列出脚本
python code/screens/run_all_screens.py screen_grp # 只跑匹配项（见脚本 --help）
```

## 脚本与数据源 / 产出（摘要）

| 脚本 | 主要数据源（`data/`） | 产出示例（`screenshots/`） |
|------|------------------------|----------------------------|
| `screen_s_class.py` | `s_class_all.json`、`s_class_new.json`、`s_class_mtd.json` | `recovery_rate_*.png`、组合图、`recovery_rate_S_table_*.png`（约 15 张量级） |
| `screen_m1.py` | `m1_assignment_repayment.json` | `assignment_repayment_*.png`、`assignment_repayment_table_*.png`（柱线 + 表图） |
| `screen_m0.py` | **`m0_billing.json`**、**`m0_billing_grouped.json`**（与 `run_all` 命名一致） | `m0_*.png`（约 8 张） |
| `screen_grp.py` | **`grp_collector.json`** | `grp_*.png`（按数据中 `case_type`，约 12 张） |
| `screen_avg_eff_worktime.py` | `avg_eff_worktim.json` 等（存在则画） | `avg_eff_worktime.png`、`avg_eff_call_worktime.png`、`avg_eff_wa_worktime.png`（1～3 张） |
| `screen_m2_m6.py` | `M2_class_all.json`、`M6_class_all.json` | `recovery_rate_M2_*.png`、`recovery_rate_M6_*.png` 及对比表（共 4 张） |
| **`screen_case_stock.py`** | **`case_stock.json`**（需含 `case_group_type`、`col_type` 等字段） | **`case_stock_9grid.png`**（3×3 柱线 + 每列下方折线数值表；详见下文） |

视觉主题见同目录 **`chart_theme.py`**（各脚本 `import chart_theme` 后 `apply_chart_theme()`）。

## `screen_case_stock.py`（人均库存看板）

- **依赖**：`data/case_stock.json`（由 `code/sql/13_case_stock.sql` 经 `run_all.py` 导出）。
- **输出**：`screenshots/case_stock_9grid.png`。
- **结构**：3 行 × 3 列——行：**人均库存 / 案件数 / 分案人数**；列：**非预测外呼 / 预测外呼 / 整体**。
- **柱**：前两列为按 **`case_group_type`** 堆叠（顺序 S1→S2→S3，组内 RA→RB→RC→RD）；**整体**列在案件数/分案人数行按 **`col_type`** 两叠；人均库存行整体列为「非预测 / 预测」两叠，高度取自 **第 1、2 列折线序列**（分列 `line_metrics` 人均库存）。
- **折线**：仅 **第一行人均库存** 绘制，透明度约 50%；**第三列**折线点为 **不拆分 `col_type`** 的整体 **`line_metrics`**（与该行第三列表格一致）；第二、三行不画折线。
- **表格**：每个子图下方一行表，填对应折线各月取值（四舍五入整数、完整数字无 k/M）；第三列第一行表 = 整体人均库存折线，与图中红线一致。
- **坐标**：图上不显示月份（表格表头为月份）；同一行内 **第 1、2 列共用 Y 轴量程**，第 3 列独立；左轴无刻度。

单独调试：

```powershell
cd code/screens
python screen_case_stock.py
```

## 输出目录与依赖

- 所有 PNG 默认写入项目根 **`screenshots/`**（脚本内 `Path(__file__).resolve().parent.parent.parent / "screenshots"`）。
- **Python**：`matplotlib`、`numpy`；`screen_grp.py` 另需 **`pandas`**。
- **字体**：需系统中文字体（如 Microsoft YaHei / SimHei / DengXian），否则标题可能方块字。

## 批处理（可选）

同目录提供 **`run_all.bat`** / **`run_all.sh`**、以及 **`run_all_screens.py`**（动态发现，新增 `screen_*.py` 会自动纳入）。**首选 `run_all_screens.py`**。

## 更多文档

- [`GRP_ROBUSTNESS.md`](GRP_ROBUSTNESS.md) — GRP 催收员缺失与对齐逻辑  
- [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md) — 迁移备忘  

## 最后更新

2026-05-02 — 重写为与当前脚本一致；修正 M0/GRP 文件名；补充 `screen_m2_m6`、`screen_case_stock` 与 `run_all_screens` 推荐用法。
