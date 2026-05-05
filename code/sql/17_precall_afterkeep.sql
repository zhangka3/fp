select 
dt,
case when stage like '%RB%' or stage in ('M2','M5') then '全时' else '手工' end as type,
stage,
sum(reserve_case_cnt)/sum(stock_case_cnt) as keep_rate,
sum(after_reserve_call_cnt)/sum(reserve_case_cnt) as avg_callcnt_percase_afterkeep,
sum(after_reserve_connect_cnt)/sum(after_reserve_call_cnt) conn_rate_afterkeep
from tmp_export.pre_call_after_reverse_call_01 a left join ec_dim.dim_ec_nn_red_days b on a.dt=replace(b.date,'-','')
where 1=1
and stage is not null
and (b.is_red_day=0 or b.is_red_day is null)
and dt>=date_format(date_sub(current_date(),60), 'yyyyMMdd')
group by 1,2,3
order by 1,2,3
;