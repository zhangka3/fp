-- full_call DATA
-- Query ID: 004
-- Purpose: 查询不同队列的电话满频率（拨打次数打到限频），拨打次数等等
-- Time Range: 最近100天 (2026-01 ~ 2026-04)
-- Expected Rows: >=800 (100 days × 9 ccase_type & rank_type)

select dt,weekofyear(dt) as weeknum,case_type,rank_type,
sum(self_full_frequency_case_cnt) as self_full_frequency_case_cnt,
sum(noself_full_frequency_case_cnt) as noself_full_frequency_case_cnt,
sum(full_frequency_case_cnt) as full_frequency_case_cnt,
SUM(call_cnt) as call_cnt,
SUM(self_call_cnt) as self_call_cnt,
SUM(noself_call_cnt) as noself_call_cnt,
sum(call_case_cnt) as call_case_cnt,
sum(self_call_rengong_novm_connected_cnt) self_call_rengong_novm_connected_cnt,
sum(self_nohusun_call_cnt) as self_nohusun_call_cnt,
sum(case_call_rengong_novm_connected_cnt) as case_call_rengong_novm_connected_cnt,
sum(case_nohusun_call_cnt) as case_nohusun_call_cnt,
sum(noself_call_rengong_novm_connected_cnt) as noself_call_rengong_novm_connected_cnt,
sum(noself_nohusun_call_cnt) as noself_nohusun_call_cnt,

sum(self_full_frequency_case_cnt)/sum(call_case_cnt) AS self_full_rate,
sum(noself_full_frequency_case_cnt)/sum(call_case_cnt) AS contact_full_rate,
sum(full_frequency_case_cnt)/sum(call_case_cnt) as total_full_rate,
sum(self_call_rengong_novm_connected_cnt)/sum(self_nohusun_call_cnt) as eff_self_con_rate,
sum(noself_call_rengong_novm_connected_cnt)/sum(noself_nohusun_call_cnt) as eff_cont_con_rate,
sum(case_call_rengong_novm_connected_cnt)/sum(case_nohusun_call_cnt) as eff_con_rate

from tmp_export.case_productivity_2025
where is_red_day='0' 
and rank_type<>'其他'
and dt>=date_format(date_sub(current_date(),100), 'yyyy-MM-dd')
and collector_type in ('EM','BPO','AP') and is_completed_t0='当日未结清'
group by 1,2,3,4
order by 1,2,3,4
