-- M2-CLASS ALL DATA
-- Query ID: 001
-- Purpose: 查询M2各案件类型在ALL口径下的每日分案、新增逾期和回款数据
-- Time Range: 最近3个月 (2026-02 ~ 2026-04)
-- Expected Rows: 234 (28+31+19 days × 3 case types)

SELECT
    p_month,
    day(p_date) as day,
    case_type,
    sum(assigned_principal) as assigned_principal,
    sum(overdue_added_principal) as overdue_added_principal,
    sum(repaid_principal) as repaid_principal
FROM tmp_export.s1_s2_s3_m2_mtd_smy
WHERE 1=1
    AND p_month >= date_format(date_sub(current_date(),90), 'yyyy-MM')
    AND p_month <= date_format(date_sub(current_date(),1), 'yyyy-MM')
    AND case_type IN ('M2')
group by p_month, day(p_date), case_type
ORDER BY p_month, day(p_date), case_type
;
