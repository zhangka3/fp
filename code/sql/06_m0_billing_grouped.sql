-- M0 BILLING DATA (GROUPED BY OVERDUE INDICATOR)
-- Query ID: 953987
-- Purpose: 查询M0每日按逾期指标分组的账单数据
-- Time Range: 从2025-05-01到2026-04-30 (365天 × 2 overdue indicators)
-- Expected Rows: 730

SELECT
    billing_date,
    c_billing_user_overdue_ind,
    sum(billing_instalment_cnt) as billing_instalment_cnt,
    sum(c_billing_instalment_cnt_pastdue_1d) as c_billing_instalment_cnt_pastdue_1d,
    sum(billing_principal) as billing_principal,
    sum(c_billing_principal_pastdue_1d) as c_billing_principal_pastdue_1d,
    sum(c_billing_principal_pastdue_2d) as c_billing_principal_pastdue_2d,
    sum(c_billing_principal_pastdue_4d) as c_billing_principal_pastdue_4d,
    sum(c_billing_principal_pastdue_6d) as c_billing_principal_pastdue_6d,
    sum(c_billing_principal_pastdue_8d) as c_billing_principal_pastdue_8d,
    sum(c_billing_principal_pastdue_9d) as c_billing_principal_pastdue_9d,
    sum(c_billing_principal_pastdue_11d) as c_billing_principal_pastdue_11d,
    sum(c_billing_principal_pastdue_13d) as c_billing_principal_pastdue_13d,
    sum(c_billing_principal_pastdue_16d) as c_billing_principal_pastdue_16d,
    sum(c_billing_principal_pastdue_31d) as c_billing_principal_pastdue_31d
FROM tmp_export.m0_smy
WHERE 1=1
    AND billing_date >= '2025-01-01'
    AND billing_date >= date_format(date_sub(current_date(),360), 'yyyy-MM-dd')
    AND billing_date <= date_format(date_sub(current_date(),1), 'yyyy-MM-dd')
    AND c_billing_user_overdue_ind IN (0, 1)
group by billing_date, c_billing_user_overdue_ind
ORDER BY billing_date, c_billing_user_overdue_ind
LIMIT 1000;
