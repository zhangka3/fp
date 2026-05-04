with base as (
select year(dt) as year,weekofyear(dt) as weeknum,concat(case_type,'-',rank_type) as case_type,
sum(self_full_frequency_case_cnt) as self_full_frequency_case_cnt,
sum(noself_full_frequency_case_cnt) as noself_full_frequency_case_cnt,
sum(full_frequency_case_cnt) as full_frequency_case_cnt,
SUM(call_cnt) as call_cnt,
SUM(self_call_cnt) as self_call_cnt,
SUM(noself_call_cnt) as noself_call_cnt,
sum(call_case_cnt) as call_case_cnt,
SUM(connected_case_cnt) as connected_case_cnt,

sum(self_call_rengong_novm_connected_cnt) self_call_rengong_novm_connected_cnt,
sum(self_nohusun_call_cnt) as self_nohusun_call_cnt,
sum(case_call_rengong_novm_connected_cnt) as case_call_rengong_novm_connected_cnt,
sum(case_nohusun_call_cnt) as case_nohusun_call_cnt,
sum(noself_call_rengong_novm_connected_cnt) as noself_call_rengong_novm_connected_cnt,
sum(noself_nohusun_call_cnt) as noself_nohusun_call_cnt,

SUM(self_call_connected_novm_duration) as self_call_connected_novm_duration,
SUM(noself_call_connected_novm_duration) as noself_call_connected_novm_duration,
SUM(call_connected_novm_duration) as call_connected_novm_duration,

sum(self_call_cnt)/sum(call_case_cnt) as avg_self_call_cnt_per_case,
sum(noself_call_cnt)/sum(call_case_cnt) as avg_noself_call_cnt_per_case,
sum(call_cnt)/sum(call_case_cnt) as avg_call_cnt_per_case,
sum(self_full_frequency_case_cnt)/sum(call_case_cnt) AS self_full_rate,
sum(noself_full_frequency_case_cnt)/sum(call_case_cnt) AS contact_full_rate,
sum(full_frequency_case_cnt)/sum(call_case_cnt) as total_full_rate,
sum(self_call_rengong_novm_connected_cnt)/sum(self_nohusun_call_cnt) as eff_self_con_rate,
sum(noself_call_rengong_novm_connected_cnt)/sum(noself_nohusun_call_cnt) as eff_cont_con_rate,
sum(case_call_rengong_novm_connected_cnt)/sum(case_nohusun_call_cnt) as eff_con_rate,

SUM(self_call_connected_novm_duration)/SUM(connected_case_cnt) as avg_self_dur_per_case,
SUM(noself_call_connected_novm_duration)/SUM(connected_case_cnt) as avg_noself_dur_per_case,
SUM(call_connected_novm_duration)/SUM(connected_case_cnt) as avg_dur_per_case

from tmp_export.case_productivity_2025
where is_red_day='0' 
and rank_type<>'其他'
and dt>=date_format(date_sub(current_date(),100), 'yyyy-MM-dd')
and collector_type in ('EM','BPO','AP') and is_completed_t0='当日未结清'
group by 1,2,3
)

select
year,weeknum,case_type,
self_full_frequency_case_cnt,
noself_full_frequency_case_cnt,
full_frequency_case_cnt,
call_cnt,
self_call_cnt,
noself_call_cnt,
call_case_cnt,
self_call_rengong_novm_connected_cnt,
self_nohusun_call_cnt,
case_call_rengong_novm_connected_cnt,
case_nohusun_call_cnt,
noself_call_rengong_novm_connected_cnt,
noself_nohusun_call_cnt,

self_full_rate,
lag(self_full_rate) over(partition by case_type order by year,weeknum) as lag_self_full_rate,
self_full_rate-lag(self_full_rate) over(partition by case_type order by year,weeknum) as self_full_rate_dif,
contact_full_rate,
lag(contact_full_rate) over(partition by case_type order by year,weeknum) as lag_contact_full_rate,
contact_full_rate-lag(contact_full_rate) over(partition by case_type order by year,weeknum) as contact_full_rate_dif,
total_full_rate,
lag(total_full_rate) over(partition by case_type order by year,weeknum) as lag_total_full_rate,
total_full_rate-lag(total_full_rate) over(partition by case_type order by year,weeknum) as total_full_rate_dif,

avg_self_call_cnt_per_case,
lag(avg_self_call_cnt_per_case) over(partition by case_type order by year,weeknum) as lag_avg_self_call_cnt_per_case,
avg_self_call_cnt_per_case-lag(avg_self_call_cnt_per_case) over(partition by case_type order by year,weeknum) as avg_self_call_cnt_per_case_dif,
avg_noself_call_cnt_per_case,
lag(avg_noself_call_cnt_per_case) over(partition by case_type order by year,weeknum) as lag_avg_noself_call_cnt_per_case,
avg_noself_call_cnt_per_case-lag(avg_noself_call_cnt_per_case) over(partition by case_type order by year,weeknum) as avg_noself_call_cnt_per_case_dif,
avg_call_cnt_per_case,
lag(avg_call_cnt_per_case) over(partition by case_type order by year,weeknum) as lag_avg_call_cnt_per_case,
avg_call_cnt_per_case-lag(avg_call_cnt_per_case) over(partition by case_type order by year,weeknum) as avg_call_cnt_per_case_dif,

eff_self_con_rate,
lag(eff_self_con_rate) over(partition by case_type order by year,weeknum) as lag_eff_self_con_rate,
eff_self_con_rate-lag(eff_self_con_rate) over(partition by case_type order by year,weeknum) as eff_self_con_rate_dif,
eff_cont_con_rate,
lag(eff_cont_con_rate) over(partition by case_type order by year,weeknum) as lag_eff_cont_con_rate,
eff_cont_con_rate-lag(eff_cont_con_rate) over(partition by case_type order by year,weeknum) as eff_cont_con_rate_dif,
eff_con_rate,
lag(eff_con_rate) over(partition by case_type order by year,weeknum) as lag_eff_con_rate,
eff_con_rate-lag(eff_con_rate) over(partition by case_type order by year,weeknum) as eff_con_rate_dif,

avg_self_dur_per_case,
lag(avg_self_dur_per_case) over(partition by case_type order by year,weeknum) as lag_avg_self_dur_per_case,
avg_self_dur_per_case-lag(avg_self_dur_per_case) over(partition by case_type order by year,weeknum) as avg_self_dur_per_case_dif,
avg_noself_dur_per_case,
lag(avg_noself_dur_per_case) over(partition by case_type order by year,weeknum) as lag_avg_noself_dur_per_case,
avg_noself_dur_per_case-lag(avg_noself_dur_per_case) over(partition by case_type order by year,weeknum) as avg_noself_dur_per_case_dif,
avg_dur_per_case,
lag(avg_dur_per_case) over(partition by case_type order by year,weeknum) as lag_avg_dur_per_case,
avg_dur_per_case-lag(avg_dur_per_case) over(partition by case_type order by year,weeknum) as avg_dur_per_case_dif

from base 
order by 3,1,2
