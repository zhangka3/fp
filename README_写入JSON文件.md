# 写入所有JSON文件 - 使用说明

> **2026-05 提示**：本文为早期「按固定 Query ID 手工写入」备忘，**表内 Query ID 与条数可能已过期**。当前周报请以根目录 **`.claude/skills/wkrpt.md`（wkrpt Skill）** 为准，使用 **`python code/python/01_execute_sql/run_all.py`** 将 **`code/sql/*.sql`（现 15 条）** 经 MCP 落盘到 **`data/*.json`**。

## 文件说明

共需要生成 **8个JSON文件**:

| 序号 | 文件名 | Query ID | 数据源 | 行数 | 状态 |
|-----|--------|----------|--------|------|------|
| 1 | s_class_all.json | 968652 | tmp_export.s1_s2_s3_m2_mtd_smy | 348 | ✓ 已完成 |
| 2 | s_class_new.json | 968653 | tmp_export.s1_s2_s3_m2_mtd_smy | 348 | ⏳ 待写入 |
| 3 | s_class_mtd.json | 968654 | tmp_export.s1_s2_s3_m2_mtd_smy | 348 | ⏳ 待写入 |
| 4 | m1_assignment_repayment.json | 968655 | dwa_id.dwa_id_col_df_mtd_assign_repayment | 234 | ⏳ 待写入 |
| 5 | grp_collector.json | 968656 | tmp_export.area_mtd01_ins | 1215 | ✓ 已完成 |
| 6 | avg_eff_worktim.json | 968657 | tmp_export.0101exp_col_collector_report | 719 | ⏳ 待写入 |
| 7 | m0_billing.json | 968671 | tmp_export.m0_smy | 360 | ✓ 已完成 |
| 8 | m0_billing_grouped.json | 968672 | tmp_export.m0_smy | 720 | ✓ 已完成 |

## 方法1: 使用Python脚本(推荐)

### 步骤1: 获取查询结果

在Claude Code中执行MCP SQL查询:

```python
# 获取4个待写入文件的查询结果
result_968653 = mcp__sql__get_query_result(queryId=968653)
result_968654 = mcp__sql__get_query_result(queryId=968654)
result_968655 = mcp__sql__get_query_result(queryId=968655)
result_968657 = mcp__sql__get_query_result(queryId=968657)
```

### 步骤2: 使用保存脚本

```python
from save_all_json_files import save_all_files

# 构建查询结果字典
query_results = {
    968653: result_968653,  # s_class_new
    968654: result_968654,  # s_class_mtd
    968655: result_968655,  # m1_assignment_repayment
    968657: result_968657,  # avg_eff_worktim
}

# 保存所有文件
save_all_files(query_results)
```

## 方法2: 手动编辑脚本

如果MCP调用有问题,可以手动编辑 `write_remaining_4_files.py`:

1. 在Claude Code中获取查询结果
2. 复制每个结果的 `rows` 数据
3. 粘贴到脚本的 `query_results` 字典中
4. 运行脚本: `python write_remaining_4_files.py`

## JSON文件格式

所有文件使用统一的metadata格式:

```json
{
  "metadata": {
    "data_fetch_date": "2026-04-27",
    "query_time": "2026-04-27 12:30:45",
    "query_id": "968653",
    "data_source": "tmp_export.s1_s2_s3_m2_mtd_smy"
  },
  "header": ["p_month", "day", "case_type", ...],
  "rows": [
    ["2026-01", "1", "S1", "2924921478.000000", ...],
    ...
  ],
  "rowCount": 348
}
```

## 验证文件

运行以下命令检查所有文件:

```bash
# 请在项目根目录（当前目录下须有 data/）执行：
python -c "
import os, json
for f in os.listdir('data'):
    if f.endswith('.json'):
        with open(f'data/{f}', 'r', encoding='utf-8') as file:
            data = json.load(file)
            print(f'{f}: {data.get(\"rowCount\", len(data))} 行')
"
```

## SQL查询文件位置

对应的SQL查询文件在:
- `code/sql/01_s_all.sql` (Query 968652)
- `code/sql/02_s_new.sql` (Query 968653)
- `code/sql/03_s_mtd.sql` (Query 968654)
- `code/sql/04_m1_assignment.sql` (Query 968655)
- `code/sql/07_grp_collector.sql` (Query 968656)
- `code/sql/08_avg_eff_worktime.sql` (Query 968657)
- `code/sql/05_m0_billing.sql` (Query 968671)
- `code/sql/06_m0_billing_grouped.sql` (Query 968672)

## 问题排查

### 问题1: Python执行被中断
**解决方案**: 数据量太大，使用小批量保存或直接编辑脚本写入

### 问题2: MCP查询超时
**解决方案**: 查询可能需要时间，检查查询状态:
```python
status = mcp__sql__get_query_status(queryId=968653)
```

### 问题3: 文件编码错误
**解决方案**: 确保使用 UTF-8 编码: `encoding='utf-8'`

## 下一步

完成所有8个文件后，运行数据验证:
```bash
python code/screens/check_data.py
```
