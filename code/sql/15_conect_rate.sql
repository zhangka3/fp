with base as (
select *,
case when call_type_code in ('I','A') then 
    case when case_id is null then '催告IVR' else '催收IVR'  end
when case_id is null then '(异常)无case_id'
when calc_frequency ='F' then '(异常)未成功呼出'
when call_type_code in ('M','N') and call_uuid is null then '(异常)手拨+多呼无call_uuid'
when call_type_code in ('M','N') and connected_ind='T' and collector_comment is null then '(异常)接通但无催记'
when call_type_code in ('M','N') and connected_ind='T' and sip_hangup_cause is null then '(异常)手拨+多呼接通但无信令码'
when connected_ind='F' and collector_comment in('VM','VM_EC','DEL_EC','NR','WP','WP_EC','CNPTP','CNPTP_EC','PTP','PTP_EC','LMS','LMS_EC') then '(异常)未接通但有有效催记'
when contact_type not in ('S','E','I','O','N') then '(异常)预期外号码'
else 'in号码质量分析范围'
END as scope
from tmp_export.col_phone_quality
where created_date>=date_format(date_sub(current_date(),120), 'yyyy-MM-dd')
)

select 
year(created_date) as year,weekofyear(created_date) as week_num,
case
when call_type_code in ('E','P') then '预测外呼'
when call_type_code in ('I') then 'IVR'
when call_type_code in ('M') then '一键多呼'
when call_type_code in ('N') then '手拨'
else '其他'
end as call_type,
count(case when connected_ind='T' and transfer_ind='F' and collector_comment not in ('VM','VM_EC') then policy_call_id end)/count(policy_call_id) as connect_rate,
count(policy_call_id) as call_cnt
from base WHERE scope='in号码质量分析范围'
group by 1,2,3
order by 1,2,3
;