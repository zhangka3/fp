-- case_stock DATA
-- Query ID: 003
-- Purpose: 查询人均库存，分案人数等等
-- Time Range: 最近4个月 (2026-01 ~ 2026-04)
-- Expected Rows: >=30 (4 mth × 9 col_type & case_group_type)

with base as (
select 
substr(dt,1,6) as mth,
dt,
case_group_type,
case 
when collector_type IN ('EM','BPO') and collector_name not like '%(RB)%' then '非预测外呼' 
when collector_type IN ('EM','BPO','AP') and collector_name like '%(RB)%' then '预测外呼'
else '其他' end as col_type,
sum(case_stock_cnt) as case_stock_cnt,
count(distinct case when iswork=1 then concat(collector_name,'-',dt) else null end) as num_col_dt
from tmp_export.case_stock_smy
where 1=1
and substr(dt,1,6)>=date_format(date_sub(current_date(),90), 'yyyyMM')
and substr(dt,1,6)<=date_format(date_sub(current_date(),1), 'yyyyMM')
and area_type='催收队列' and is_red_day='0'
and (case_group_type like '%S1%' or case_group_type like '%S2%' or case_group_type like '%S3%')
group by 1,2,3,4
)

select 
mth,case_group_type,col_type,
sum(case_stock_cnt) as case_stock_cnt,
count(distinct dt) as num_dt,
sum(case_stock_cnt)/count(distinct dt) as avg_case_stock_cnt_daily,
sum(num_col_dt)/count(distinct dt) as avg_num_col_daily,
(sum(case_stock_cnt)/count(distinct dt))/(sum(num_col_dt)/count(distinct dt)) as avg_case_stock_cnt_daily_percol
from base 
where col_type<>'其他' 
group by 1,2,3
having sum(case_stock_cnt)>0
order by 1,2,3
;
