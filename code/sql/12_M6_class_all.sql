-- M6-CLASS ALL DATA
-- Query ID: 002
-- Purpose: 查询M2-M6在ALL口径下的每日分案、新增逾期和回款数据
-- Time Range: 最近3个月 (2026-02 ~ 2026-04)
-- Expected Rows: 234 (28+31+19 days × 3 case types)

SELECT
    p_month,
    day(p_date) as day,
    sum(assigned_principal) as assigned_principal,
    sum(overdue_added_principal) as overdue_added_principal,
    sum(repaid_principal) as repaid_principal
FROM tmp_export.m2_mtd_smy
WHERE 1=1
    and installment_max_overdue_days>=31
    and installment_max_overdue_days<=180
    AND p_month >= date_format(date_sub(current_date(),90), 'yyyy-MM')
    AND p_month <= date_format(date_sub(current_date(),1), 'yyyy-MM')
group by p_month, day(p_date)
ORDER BY p_month, day(p_date)
;
