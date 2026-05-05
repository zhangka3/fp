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
| 14_full_call.sql | full_call.json | tmp_export.case_productivity_2025 | **周粒度**：`year` + `weekofyear(dt)` + **`concat(case_type,'-',rank_type)` 作为输出列 `case_type`**；满频/接通汇总 + **案均拨打** + **案均有效通时**（`avg_self_dur_per_case` 等，见下）+ **`lag` / 周环比 `*_dif`**。过滤：近 100 天、非红休、`collector_type`、首期状态等见 SQL。出图：**`screen_full_call.py`** → `full_call_full_rates.png`、`full_call_avg_calls_per_case.png`、`full_call_avg_dur_per_case.png`、`full_call_eff_rates.png`（最近 5 周；生成顺序：满频→案均拨打→案均通时→接通率） | 约 **100～200** 行量级（随周数 × 复合类型数变化；非旧版「日×多维」上千行） |
| 15_conect_rate.sql | conect_rate.json | tmp_export.col_phone_quality | **周粒度**：`year(created_date)`、`weekofyear(created_date)` 为 **`week_num`**；**`call_type`** 由 `call_type_code` 映射（预测外呼 / IVR / 一键多呼 / 手拨 / 其他）；**`connect_rate`** = 有效接通通次 / 通次（见 SQL）；**`call_cnt`** = `count(policy_call_id)`。仅 **`scope='in号码质量分析范围'`**；`created_date` 约 **120** 天窗口。出图：**`screen_call_type_weekly.py`** → `call_type_weekly_connect.png` | 约 **周数 × 5 call_type** 行量级 |
| 16_precall_task.sql | precall_task.json | `tmp_export.pre_call_01` 等（见 SQL） | **日 × `pre_type`（手工/全时）× `stage`**：`conn_ratio`、`conn_loss_ratio`、`eff_duration_ratio`、`vm_ratio_agent_conn`；`call_create_date` 约 **60** 天；排除部分 `task_id`。出图：**`screen_precall_task.py`** → **`precall_task_trends.png`** | 随组合数变化 |
| 17_precall_afterkeep.sql | precall_afterkeep.json | `tmp_export.pre_call_after_reverse_call_01` | **日 × 手工/全时 × `stage`**：`keep_rate`、`avg_callcnt_percase_afterkeep`、`conn_rate_afterkeep`；首列 **`mm_dd`**；`dt` 约 **60** 日。出图：**`screen_precall_afterkeep.py`** → **`precall_afterkeep_trends.png`** | 随组合数变化 |

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

### precall_task（16）

- **粒度**：按 `call_create_date`（导出为 MM-dd）、**`pre_type`**（全时 / 手工）、**`stage`** 聚合；指标含 **`conn_loss_ratio`**（呼损）、**`conn_ratio`**、**`eff_duration_ratio`**、**`vm_ratio_agent_conn`**。
- **时间**：约 **`current_date() − 60`** 起；过滤 **`pre_type`/`stage` 非空**及排除 `task_id`（见 SQL）。
- **图表**：`code/screens/screen_precall_task.py` → `screenshots/precall_task_trends.png`（详见 `code/screens/README.md`）。
- **校验**：`validate_precall_task`（`VALIDATORS['precall_task.json']`）。

### precall_afterkeep（17）

- **粒度**：按 **`mm_dd`**（由 `dt` 推导）、**`pre_type`**（全时 / 手工，与 SQL16 同规则）、**`stage`**；指标 **`keep_rate`**、**`avg_callcnt_percase_afterkeep`**、**`conn_rate_afterkeep`**。
- **时间**：`dt >= date_sub(current_date(),60)`（`yyyyMMdd`）；源表 **`tmp_export.pre_call_after_reverse_call_01`**。
- **图表**：`code/screens/screen_precall_afterkeep.py` → `screenshots/precall_afterkeep_trends.png`（版式对齐 `precall_task_trends`）。
- **校验**：`validate_precall_afterkeep`（`VALIDATORS['precall_afterkeep.json']`）。

### full_call（14）

- **结构**：`WITH base AS (...)` 内按 **`year(dt)`、`weekofyear(dt)`、`concat(case_type,'-',rank_type) AS case_type`** 聚合；外层再 `SELECT` 并加窗口函数 **`lag(rate) OVER (PARTITION BY case_type ORDER BY year, weeknum)`** 及 **`rate - lag`** 得到各比率的 **`lag_*` / `*_dif`**（同一复合类型下的**周环比**）。
- **时间**：源表 `dt` 取最近约 **100 天**；`is_red_day='0'`；`rank_type` 排除「其他」（以 SQL 字面为准）；`collector_type in ('EM','BPO','AP')`；`is_completed_t0` 等条件见脚本。
- **输出列**：除各 `*_cnt` 外，含 **`avg_self_call_cnt_per_case` / `avg_noself_call_cnt_per_case` / `avg_call_cnt_per_case`**（案均拨打）与 **`avg_self_dur_per_case` / `avg_noself_dur_per_case` / `avg_dur_per_case`**（案均有效通时）及各自 **`lag_*` / `*_dif`**；以及 `self_full_rate`、`contact_full_rate`、`total_full_rate`、`eff_*` 等率及其 **lag / dif**；**无单独 `dt`、`rank_type` 列**（`rank_type` 已拼进 `case_type`）。
- **用途**：生产力/外呼质量周序列表；出图见 **`code/screens/screen_full_call.py`**（`code/screens/README.md`）。
- **维护**：改聚合粒度或别名后，请同步 **`03_validate_data` 中 `validate_full_call`** 与本 README「查询列表」期望行数说明。

#### `full_call.json` 字段含义（`data/full_call.json`）

以下为 **`14_full_call.sql` → `full_call.json`** 中与业务直接相关的 **计数、次数、案均拨打、案均有效通时、比率** 列说明（另有 **`year` / `weeknum` / 复合 `case_type`** 为维度；各比率与案均类指标对应的 **`lag_*`、`*_dif`** 为按周序的上周值与环比差，见上文「结构」）。

1. **满频相关案件数（计数）**
   - **`self_full_frequency_case_cnt`**：本人号码拨打到频次上限的**案件数**。
   - **`noself_full_frequency_case_cnt`**：非本人号码拨打到频次上限的**案件数**。
   - **`full_frequency_case_cnt`**：所有号码拨打到频次上限的**案件数**。

2. **拨打次数**
   - **`call_cnt`**：所有号码的拨打次数。
   - **`self_call_cnt`**：本人号码的拨打次数。
   - **`noself_call_cnt`**：非本人号码的拨打次数。

3. **有拨打的案件数**
   - **`call_case_cnt`**：所有有拨打记录的**案件数**。

4. **非呼损拨打与有效接通（次数 / 案件数）**
   - **`self_call_rengong_novm_connected_cnt`**：本人、非呼损拨打后的**有效接通次数**。
   - **`self_nohusun_call_cnt`**：本人**非呼损拨打次数**。
   - **`case_call_rengong_novm_connected_cnt`**：所有（本人+非本人）非呼损拨打后的**有效接通案件数**。
   - **`case_nohusun_call_cnt`**：所有**非呼损拨打的案件数**。
   - **`noself_call_rengong_novm_connected_cnt`**：非本人、非呼损拨打后的**有效接通次数**。
   - **`noself_nohusun_call_cnt`**：非本人**非呼损拨打次数**。

5. **比率（在 `base` 聚合层按周、按复合 `case_type` 计算）**
   - **`self_full_rate`**：**本人满频率**（见下式）。
   - **`contact_full_rate`**：**非本人满频率**（下式中对应非本人满频案件数 / 有拨打案件数）。
   - **`total_full_rate`**：**整体满频率**。
   - **`eff_self_con_rate`**：**本人有效接通率**。
   - **`eff_cont_con_rate`**：**非本人有效接通率**。
   - **`eff_con_rate`**：**整体有效接通率**。

6. **案均拨打次数（在 `base` 聚合层按周、按复合 `case_type` 计算）**

   分母均为 **`call_case_cnt`**（有拨打记录的案件数）；分子为对应维度的拨打次数合计，结果表示**每件有拨打案件平均被拨打多少次**。

   - **`avg_self_call_cnt_per_case`**：**本人案均拨打次数** = `sum(self_call_cnt) / sum(call_case_cnt)`。
   - **`avg_noself_call_cnt_per_case`**：**非本人案均拨打次数** = `sum(noself_call_cnt) / sum(call_case_cnt)`。
   - **`avg_call_cnt_per_case`**：**整体案均拨打次数**（本人+非本人）= `sum(call_cnt) / sum(call_case_cnt)`。

   外层对上述三列同样输出 **`lag_*`** 与 **`*_dif`**（与满频、接通率列的窗口定义一致：`PARTITION BY case_type ORDER BY year, weeknum`）。

7. **案均有效通时（在 `base` 聚合层按周、按复合 `case_type` 计算）**

   `base` 中先对源表字段 **`self_call_connected_novm_duration` / `noself_call_connected_novm_duration` / `call_connected_novm_duration`** 做周粒度 **`sum`**（非呼损侧**有效接通**相关时长合计）；分母均为 **`connected_case_cnt`**（**有接通**的案件数合计）。得到的 **`avg_*_dur_per_case`** 表示：**平均每件有接通案件**所摊到的该类通时（本人 / 非本人 / 整体）。**时长单位与源表 `*_duration` 字段一致**（一般为秒；若有换算以数仓为准）。

   - **`avg_self_dur_per_case`**：**本人案均有效通时** = `sum(self_call_connected_novm_duration) / sum(connected_case_cnt)`。
   - **`avg_noself_dur_per_case`**：**非本人案均有效通时** = `sum(noself_call_connected_novm_duration) / sum(connected_case_cnt)`。
   - **`avg_dur_per_case`**：**整体案均有效通时** = `sum(call_connected_novm_duration) / sum(connected_case_cnt)`。

   外层对上述三列同样输出 **`lag_*`** 与 **`*_dif`**（窗口同前）。

8. **上述率在 SQL 中的计算公式**（与 `14_full_call.sql` 中 `base` CTE 一致；均为 **`sum(分子) / sum(分母)`** 在周粒度上的聚合比）

```sql
sum(self_full_frequency_case_cnt) / sum(call_case_cnt) AS self_full_rate,
sum(noself_full_frequency_case_cnt) / sum(call_case_cnt) AS contact_full_rate,
sum(full_frequency_case_cnt) / sum(call_case_cnt) AS total_full_rate,
sum(self_call_rengong_novm_connected_cnt) / sum(self_nohusun_call_cnt) AS eff_self_con_rate,
sum(noself_call_rengong_novm_connected_cnt) / sum(noself_nohusun_call_cnt) AS eff_cont_con_rate,
sum(case_call_rengong_novm_connected_cnt) / sum(case_nohusun_call_cnt) AS eff_con_rate
```

**案均拨打在 SQL 中的定义**（同在 `base` CTE）：

```sql
sum(self_call_cnt) / sum(call_case_cnt) AS avg_self_call_cnt_per_case,
sum(noself_call_cnt) / sum(call_case_cnt) AS avg_noself_call_cnt_per_case,
sum(call_cnt) / sum(call_case_cnt) AS avg_call_cnt_per_case
```

**环比列**：对 `self_full_rate`、`contact_full_rate`、`total_full_rate`、`eff_self_con_rate`、`eff_cont_con_rate`、`eff_con_rate`，以及 **`avg_self_call_cnt_per_case`、`avg_noself_call_cnt_per_case`、`avg_call_cnt_per_case`**，以及 **`avg_self_dur_per_case`、`avg_noself_dur_per_case`、`avg_dur_per_case`**，均输出 **`lag(...) OVER (PARTITION BY case_type ORDER BY year, weeknum)`** 及 **`当前值 - lag`** 的 **`*_dif`**（首周 `lag_*`、`*_dif` 可为 NULL）。

**案均有效通时在 SQL 中的定义**（同在 `base` CTE）：

```sql
SUM(self_call_connected_novm_duration) / SUM(connected_case_cnt) AS avg_self_dur_per_case,
SUM(noself_call_connected_novm_duration) / SUM(connected_case_cnt) AS avg_noself_dur_per_case,
SUM(call_connected_novm_duration) / SUM(connected_case_cnt) AS avg_dur_per_case
```

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

1. **提交查询**：对本目录下（当前 **16** 个）SQL 按需提交到 SMART。
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
- full_call：`year`（字符串化年）、`weeknum`（年内周序号）、`case_type`（实为 **`案件类型-排名类型`** 复合键）。

### NULL 与特殊逻辑

- **S-MTD**：rate 可能超过 100%，属业务口径。
- **M0 Grouped**：按逾期用户标识分组，行数约为单表汇总的两倍量级。
- **人均工时**：环比差值在未满月或无上月可比时可能为 NULL。
- **full_call**：每个复合 `case_type` 的**第一周**无上周可比，各指标的 **`lag_*`、`*_dif`**（含案均拨打、案均有效通时）可为 **NULL**；分母为 0 时比率、案均拨打或案均通时可为 **NULL**。

## 数据输出

所有查询结果默认保存到项目根下的 **`data/`**（文件名与上表「输出 JSON」一致）。该目录内 JSON **已被 `.gitignore` 忽略**，不会进入 Git。

## 最后更新

2026-05-03 — 补充 `case_stock` 落盘粒度（含 `case_group_type`）及与大屏脚本交叉引用；此前 2026-05-01 已对齐 08～13 号 SQL 与 JSON 命名约定。  
2026-05-03 — 新增 **`14_full_call.sql` → `full_call.json`**（生产力全量外呼口径）及本节「数据时间范围」说明。  
2026-05-03 — **`full_call` 改为周粒度 + 复合 `case_type` + `lag`/环比列**；更新查询表期望行数、时间范围与 NULL 说明；与 `validate_full_call` 对齐。  
2026-05-03 — 补充 **`full_call.json` 字段含义**（满频/拨打/非呼损接通及各率公式与环比列说明）。  
2026-05-03 — 补充 **`screen_full_call.py`** 产出 PNG 与查询表交叉引用。  
2026-05-03 — **`full_call`** 增加案均拨打：`avg_self_call_cnt_per_case`、`avg_noself_call_cnt_per_case`、`avg_call_cnt_per_case` 及 **`lag_*` / `*_dif`**；更新字段表与环比说明；已重跑 `14_full_call.sql` 落盘。  
2026-05-04 — **`full_call`** 增加案均有效通时（duration）：`avg_self_dur_per_case`、`avg_noself_dur_per_case`、`avg_dur_per_case` 及 **`lag_*` / `*_dif`**（`base` 内对 `*_connected_novm_duration` 求和，分母 `connected_case_cnt`）；更新字段表、环比与 NULL 说明；已重跑落盘；`validate_full_call` 校验列补充 `avg_dur_per_case`。  
2026-05-04 — **`screen_full_call.py`** 增加产出 **`full_call_avg_dur_per_case.png`**（与满频/案均拨打/接通率同版式；纵轴标注秒/案）。  
2026-05-04 — 新增 **`15_conect_rate.sql` → `conect_rate.json`**（周 × `call_type` 接通率与拨打量）；**`screen_call_type_weekly.py`** → **`call_type_weekly_connect.png`**；SQL 总数 **15**；`validate_data` 注册 **`conect_rate.json`**。  
2026-05-04 — 飞书 **`generate_feishu_report.py`** 从 **`m0_billing_grouped.json`** 派生模板占位符（ind0/ind1 月 7d、IND1 占比等），与 **`06_generate_feishu`** / 根目录 **wkrpt** Skill 同步说明。  
2026-05-06 — 新增 **`16_precall_task.sql` → `precall_task.json`**（预测试任务）；**`validate_data`** 注册 **`precall_task.json`**；**`screen_precall_task.py`**；SQL 总数 **16**；飞书模板含 **`precall_task_trends.png`**（插图数以 **5.5** 为准，当前约 **39**）。
