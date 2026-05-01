# SQL 查询说明文档

本目录包含周报数据提取的全部 SQL。执行方式见文末；**`run_all.py` 会将 `NN_xxx.sql` 落盘为 `data/xxx.json`**（去掉文件名前的数字与下划线前缀）。

**维护约定**：每新增或下线一个 `.sql` 文件，请同步更新本文件的「查询列表」及下方「数据输出」「数据时间范围」等章节。

## 查询列表

| 文件 | 输出 JSON | 主要数据源 | 说明 | 期望行数（量级） |
|------|-----------|------------|------|------------------|
| 01_s_class_all.sql | s_class_all.json | tmp_export.s1_s2_s3_m2_mtd_smy | S 类案件 ALL 口径（S1/S2/S3） | ~234 |
| 02_s_class_new.sql | s_class_new.json | 同上 | S 类 NEW 口径 | ~234 |
| 03_s_class_mtd.sql | s_class_mtd.json | 同上 | S 类 MTD 累积 | ~234 |
| 04_m1_assignment_repayment.sql | m1_assignment_repayment.json | dwa_id.dwa_id_col_df_mtd_assign_repayment | M1 分案回款 | ~156+ |
| 05_m0_billing.sql | m0_billing.json | tmp_export.m0_smy | M0 账单明细 | ~365+ |
| 06_m0_billing_grouped.sql | m0_billing_grouped.json | tmp_export.m0_smy | M0 按用户逾期标识分组 | ~730+ |
| 07_grp_collector.sql | grp_collector.json | tmp_export.area_mtd01_ins | GRP 催收员/区域 | ~1000+ |
| 08_avg_eff_worktim.sql | avg_eff_worktim.json | tmp_export.0101exp_col_collector_report | 人均有效工作时长（整体：通话+WA） | >200 |
| 09_avg_eff_call_worktim.sql | avg_eff_call_worktim.json | 同上 | 人均有效工作时长（仅通话） | >200 |
| 10_avg_eff_wa_worktim.sql | avg_eff_wa_worktim.json | 同上 | 人均有效工作时长（仅 WA） | >200 |
| 11_M2_class_all.sql | M2_class_all.json | tmp_export.s1_s2_s3_m2_mtd_smy | M2 ALL 口径日粒度分案/逾期/回款 | ~234 |
| 12_M6_class_all.sql | M6_class_all.json | tmp_export.m2_mtd_smy | M6（逾期 31–180 天）ALL 口径日粒度汇总 | ~234 |
| 13_case_stock.sql | case_stock.json | tmp_export.case_stock_smy | 人均库存、分案人力等；落盘粒度含 **`mth` + `case_group_type` + `col_type`**（供 `screen_case_stock.py` 堆叠） | 随月份 × 分组数变化 |

实际 **query_id** 以每次运行后 `data/*.json` 内 `metadata.query_id` 为准。

## 数据时间范围

### S-CLASS（01～03）与 M2（11）

- **时间窗口**：动态最近约 3 个月（以脚本内 `date_sub(current_date(), …)` 为准）。
- **分组**：`p_month`、`day`、`case_type`（S1/S2/S3；11 号为 M2）。
- **字段**：assigned_principal、overdue_added_principal、repaid_principal、rate（口径见各 SQL）。

### M1（04）

- **快照**：`dt` 等为脚本内约定截止日。
- **注意**：需过滤 `repaid_principal` 或 `repaid_case_cnt` 为 NULL 的记录（校验脚本侧）。

### M0（05～06）

- **时间**：账单日滚动窗口（约一年量级，见 SQL）。
- **Grouped**：增加 `c_billing_user_overdue_ind`（0/1），行数约为未分组版本的 2 倍量级。

### GRP（07）

- **时间**：通常为最近 2 个自然月（`yyyyMM`）。
- **字段**：p_month、collection_area、case_type、assigned_principal 等。

### 人均工时（08～10）

- **时间**：约最近 3 个自然月的工作日可比维度（`scope_x`：WK-WD）。
- **数据源**：催收日报汇聚表；过滤库存、工时阈值、非节假日、排除 TL/PreCall 等（见 SQL）。

### M6（12）

- **范围**：`installment_max_overdue_days` 在 31～180 天的分期维度。
- **分组**：按 `p_month`、`day(p_date)` 汇总（无 case_type 分列时为聚合口径）。

### case_stock（13）

- **时间**：`dt` 最近约 3 个月（`yyyyMM`）。
- **SQL 分组**：`mth`、`case_group_type`、`col_type`（非预测外呼 / 预测外呼；已排除「其他」）。
- **JSON 字段**：`case_stock_cnt`、`num_dt`、`avg_case_stock_cnt_daily`、`avg_num_col_daily`、`avg_case_stock_cnt_daily_percol` 等（见查询 SELECT）。
- **图表**：`code/screens/screen_case_stock.py` → `screenshots/case_stock_9grid.png`（详见 `code/screens/README.md`）。

## 数据库引擎

所有查询使用 **SMART 引擎**（Hive SQL 语法）。

## 执行方式

### 项目内一键落盘（推荐）

在项目根目录：

```bash
python code/python/01_execute_sql/run_all.py           # 执行目录下全部 .sql
python code/python/01_execute_sql/run_all.py --list    # 仅列出待执行文件
python code/python/01_execute_sql/run_all.py 13_case_stock   # 仅执行指定脚本（不带 .sql）
```

依赖：`~/.cursor/mcp.json` 中 `mcpServers.sql` 的 `url` 与 `headers`（含可用 `X-API-Key`）。

### 通过 MCP 工具（示意）

与 Cursor / HTTP MCP 集成时，典型流程为：`submit_query` → 轮询 `get_query_status` → `get_query_result`。

## 数据处理流程

1. **提交查询**：对本目录下（当前 **13** 个）SQL 按需提交到 SMART。
2. **等待完成**：轮询至 `FINISHED`。
3. **获取结果**：读取 header、rows、rowCount。
4. **保存 JSON**：写入 `../../data/`，并写入 `metadata`（含 `data_fetch_date`、`query_id`、`data_source` 等）。

## 注意事项

### 日期格式

- S-CLASS / M2：`p_month`（YYYY-MM）、日粒度字段见 SQL。
- M1：`assigned_month`、`month_day` 等。
- M0：`billing_date`（YYYY-MM-DD）。
- GRP：`p_month`（YYYYMM）。
- case_stock：`mth`（YYYYMM）、`dt`（YYYYMMDD）。

### NULL 与特殊逻辑

- **S-MTD**：rate 可能超过 100%，属业务口径。
- **M0 Grouped**：按逾期用户标识分组，行数约为单表汇总的两倍量级。
- **人均工时**：环比差值在未满月或无上月可比时可能为 NULL。

## 数据输出

所有查询结果默认保存到项目根下的 **`data/`**（文件名与上表「输出 JSON」一致）。该目录内 JSON **已被 `.gitignore` 忽略**，不会进入 Git。

## 最后更新

2026-05-03 — 补充 `case_stock` 落盘粒度（含 `case_group_type`）及与大屏脚本交叉引用；此前 2026-05-01 已对齐 08～13 号 SQL 与 JSON 命名约定。
