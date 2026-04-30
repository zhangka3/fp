-- M0 BILLING DATA
-- Query ID: 953986
-- Purpose: 查询M0每日的账单数据，包括账单金额、逾期金额等指标
-- Time Range: 从2025-05-01到2026-04-30 (365天)
-- Expected Rows: 365
--
-- 字段说明：
--   billing_instalment_cnt: 账单件数
--   instalment_cnt_pastdue_1d: 逾期1天件数
--   billing_principal: 账单金额
--   principal_pastdue_Xd: 逾期X天金额

SELECT
    billing_date,
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
group by billing_date
ORDER BY billing_date

