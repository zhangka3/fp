-- GRP COLLECTOR ASSIGNMENT DATA
-- Query ID: 953988
-- Purpose: 查询催收员按案件类型的分案和回款数据
-- Time Range: 最近2个月 (202603 ~ 202604)
-- Expected Rows: 1045
--
-- 字段说明：
--   mth: 月份 (YYYYMM格式)
--   dt: 日期 (DD格式)
--   case_type: 案件类型
--   collector_ins: 催收员/区域标识
--   repaid_principal: 回款金额
--   mtd_daily_assign_amt: MTD累积分案金额

SELECT
    mth,
    day(date) as dt,
    case_type,
    collector_ins,
    sum(repaid_principal) as repaid_principal,
    sum(mtd_daily_assign_amt) as mtd_daily_assign_amt
FROM tmp_export.area_mtd01_ins
WHERE 1=1
    AND mth IN (date_format(date_sub(current_date(),50), 'yyyyMM'), date_format(date_sub(current_date(),1), 'yyyyMM'))
group by mth, day(date), case_type, collector_ins
ORDER BY mth, day(date), case_type, collector_ins
