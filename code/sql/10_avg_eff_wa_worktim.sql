-- Average Effective Working Time DATA
-- Query ID: 954002
-- Purpose: 查询各模块下相同可比日的人均有效工作时长，以及和上月同样可比日的差距
-- Time Range: 最近3个月 (202602 ~ 202604)
-- Expected Rows: >200 行
--
-- 字段说明：
--   area_type: 模块
--   area_ranking_type: 队列
--   p_month: 月份 (YYYY-MM格式)
--   scope_x: 横坐标的分类，WK后的数字表示当月第几个7天，WD后的数据代表是周几
--   avg_eff_worktime: 人均有效工作时长
--   lag_avg_eff_worktime: 上个月同一个scope_x下人均有效工作时长
--   diff_avg_eff_worktime: 本月同上月的人均有效工作时长之差

with base as (
select area_type,area_ranking_type,p_month,scope_x,
count(distinct collector_name) as num_col,AVG(wa_minutes) as avg_eff_worktime
from (
select 
*,
substr(p_date,1,7) as p_month,
concat('WK' , ceiling(day(p_date)/7)  , "-WD" , dayofweek(p_date) ) as scope_x
from tmp_export.0101exp_col_collector_report
where 
substr(p_date,1,7) >= date_format(date_sub(current_date(), 60), 'yyyy-MM')
and
substr(p_date,1,7) <= date_format(date_sub(current_date(), 1), 'yyyy-MM')
and case_stock_cnt > 0 and calling_minutes+wa_minutes>60
and is_red_day = '0' 
and collector_name not like '%TL%'
and collector_name not like '%PreCall%'
and collector_name not like '%precall%'
) t
group by 1,2,3,4
) 
select area_type,area_ranking_type,p_month,scope_x,avg_eff_worktime,
lag(avg_eff_worktime) over(partition by area_type,area_ranking_type,scope_x order by p_month) as last_avg_eff_worktime,
case 
when p_month<date_format(date_sub(current_date(), 1), 'yyyy-MM') or lag(avg_eff_worktime) over(partition by area_type,area_ranking_type,scope_x order by p_month) is null then null
else avg_eff_worktime-lag(avg_eff_worktime) over(partition by area_type,area_ranking_type,scope_x order by p_month) end as diff_avg_eff_worktime
from base
order by 1,2,4,3
;
