# SQL查询说明文档

本目录包含周报数据提取的所有SQL查询。

## 查询列表

| 文件 | 查询ID | 数据源 | 说明 | 期望行数 |
|------|--------|--------|------|----------|
| 01_s_class_all.sql | 953982 | tmp_export.s1_s2_s3_m2_mtd_smy | S类案件ALL口径数据 | 234 |
| 02_s_class_new.sql | 953983 | tmp_export.s1_s2_s3_m2_mtd_smy | S类案件NEW口径数据 | 234 |
| 03_s_class_mtd.sql | 953984 | tmp_export.s1_s2_s3_m2_mtd_smy | S类案件MTD累积数据 | 234 |
| 04_m1_assignment_repayment.sql | 953985 | dwa_id.dwa_id_col_df_mtd_assign_repayment | M1分案回款数据 | 156 |
| 05_m0_billing.sql | 953986 | tmp_export.m0_smy | M0账单数据 | 365 |
| 06_m0_billing_grouped.sql | 953987 | tmp_export.m0_smy | M0分组账单数据 | 730 |
| 07_grp_collector.sql | 953988 | tmp_export.area_mtd01_ins | 催收员区域数据 | 1045 |

## 数据时间范围

### S-CLASS (ALL/NEW/MTD)
- **时间范围**: 2026-02-01 ~ 2026-04-19 (3个月)
- **分组**: 按月份(p_month)、日期(day)、案件类型(case_type)
- **案件类型**: S1, S2, S3
- **字段**: assigned_principal, overdue_added_principal, repaid_principal, rate

### M1
- **时间范围**: 2026-02 ~ 2026-04 (3个月)
- **快照日期**: dt='20260419'
- **案件类型**: 新案, 老案
- **字段**: assigned_principal, assigned_case_cnt, repaid_principal, repaid_case_cnt
- **注意**: 需过滤repaid_principal或repaid_case_cnt为NULL的记录

### M0
- **时间范围**: 2025-05-01 ~ 2026-04-30 (365天)
- **字段**: billing_date, billing_instalment_cnt, instalment_cnt_pastdue_Xd, repaid_instalment_cnt_Xd
- **分组版本**: 增加c_billing_user_overdue_ind字段 (0或1)

### GRP
- **时间范围**: 202603 ~ 202604 (2个月)
- **字段**: p_month, collection_area, case_type, assigned_principal, assigned_case_cnt, overdue_added_principal

## 数据库引擎

所有查询使用 **SMART 引擎**（Hive SQL语法）

## 执行方式

### 通过MCP SQL工具
```python
# 提交查询
result = mcp_sql_submit_query(
    sql=query_text,
    engine='SMART',
    maxRows=500
)

# 等待完成
status = mcp_sql_get_query_status(queryId=result['queryId'])

# 获取结果
data = mcp_sql_get_query_result(queryId=result['queryId'])
```

### 通过命令行
```bash
# 读取SQL文件
sql=$(cat 01_s_class_all.sql)

# 提交到数据仓库执行
# (具体执行方式根据实际环境配置)
```

## 数据处理流程

1. **提交查询** → 7个SQL查询提交到SMART引擎
2. **等待完成** → 轮询查询状态直到FINISHED
3. **获取结果** → 提取查询结果的rows数据
4. **数据处理** → 按需处理（日期格式、NULL值等）
5. **保存JSON** → 保存到 `data/*.json` 文件

## 注意事项

### 日期格式
- S-CLASS: 使用 `p_month` (YYYY-MM) 和 `day` (YYYY-MM-DD)
- M1: 使用 `assigned_month` (YYYY-MM) 和 `month_day` (YYYY-MM-DD)
- M0: 使用 `billing_date` (YYYY-MM-DD)
- GRP: 使用 `p_month` (YYYYMM)

### NULL值处理
- S-CLASS: rate字段的NULL或'0E-10'应转换为0.0
- M1: 过滤掉repaid_principal或repaid_case_cnt为NULL的记录

### 特殊逻辑
- **S-MTD**: rate字段是累积回款率，可能超过100%，这是正常的业务逻辑
- **M0 Grouped**: 按c_billing_user_overdue_ind分组，结果行数是单表的2倍

## 数据输出

所有查询结果保存到 `../../data/` 目录：
- s_class_all.json
- s_class_new.json
- s_class_mtd.json
- m1_assignment_repayment.json
- m0_data.json
- m0_data_grouped.json
- grp_data.json

## 最后更新

2026-04-20 - 初始版本
