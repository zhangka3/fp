-- M1 ASSIGNMENT & REPAYMENT DATA
-- Query ID: 953985
-- Purpose: 查询M1案件每日的分案金额、案件数和回款金额、案件数
-- Time Range: 最近3个月 (2026-02 ~ 2026-04)
-- Expected Rows: 156 (after filtering NULL values)
--
-- NOTE:
-- - 包含"新案"和"老案"两种case_type
-- - 需要过滤repaid_principal或repaid_case_cnt为NULL的记录

SELECT
    assigned_month,
    month_day,
    case_type,
    assigned_principal,
    assigned_case_cnt,
    repaid_principal,
    repaid_case_cnt
FROM dwa_id.dwa_id_col_df_mtd_assign_repayment
WHERE 
    dt = date_format(date_sub(current_date(),1), 'yyyyMMdd')
    AND assigned_month >= date_format(date_sub(current_date(),90), 'yyyy-MM')
    AND assigned_month <= date_format(date_sub(current_date(),1), 'yyyy-MM')
    AND case_type IN ('新案', '老案')
ORDER BY assigned_month, month_day, case_type
;
