with task_type as (
select distinct dt,task_id,num_ins,type,
case
when type='AT' then '全时'
when type='MT' then '手工'
else null end as pre_type
 from (
select a.*,a.id as task_id,length(queueid)-length(replace(queueid,',',''))+1 as num_ins,b.available
from(
select *,
get_json_object(case_source_config, '$.collectorId') as collectorId,
get_json_object(incoming_config, '$.queueIds') as queueid
from tmp_export.ods_mysql_ec_collection_prod_col_auto_dial_task_df --where id=235
where deleted='T'
) a
left join ec_dim.dim_ec_df_admin_user_area b on a.collectorId=b.collector_Id and a.dt=b.dt
) t
)

select 
date_format(call_create_date, 'MM-dd'),
--weekofyear(date_add(call_create_date,1)) as weeknum,
pre_type,stage,
sum(conn_cnt-agent_conn_cnt)/sum(conn_cnt) as conn_loss_ratio,
sum(conn_cnt)/sum(call_cnt) as conn_ratio,
SUM(avg_eff_duration)/SUM(batch_duration/1000) as eff_duration_ratio,
sum(agent_conn_vm_cnt)/sum(agent_conn_cnt) as vm_ratio_agent_conn
from (
select a.*,b.pre_type
from tmp_export.pre_call_01 a left join task_type b on a.task_id=b.task_id and replace(a.call_create_date,'-','')=b.dt
) r
where 1=1
and r.pre_type is not NULL 
and stage is not null 
and task_id not in (184,336)
and call_create_date>=date_sub(current_date(),60)
group by 1,2,3
order by 1,2,3