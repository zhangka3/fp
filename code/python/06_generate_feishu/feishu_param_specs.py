# -*- coding: utf-8 -*-
"""飞书周报 `{占位符}` 的文档说明：含义、口径、数据源、关联 PNG。

新增脚本可计算参数时：请同步扩充 IMPLEMENTED_TEXT_PARAMS 与 TEXT_PARAM_SPECS。
模板新增占位符但未实现计算时：比对步骤会标红提示，对照表中「状态」为 待实现。
"""

from __future__ import annotations

# 当前 generate_feishu_report 中已有计算逻辑（含默认值）的文本占位符
IMPLEMENTED_TEXT_PARAMS: frozenset[str] = frozenset(
    {
        "mm",
        "mm1",
        "mm2",
        "DD",
        "DD1",
        "rate_prin_od",
        "rate_cnt_od",
        "rate_prin_od_dif",
        "rate_cnt_od_dif",
        "wk_colrate7d",
        "wk_colrate7d_dif",
        "wk_colrate15d",
        "wk_colrate15d_dif",
        "mth_colrate7d",
        "mth_colrate7d_dif",
        "mth_colrate30d",
        "mth_colrate30d_dif",
        "mth_colrate7d_ind0",
        "mth_colrate7d_ind0_dif",
        "mth_colrate7d_ind1",
        "mth_colrate7d_ind1_dif",
        "mth_ind1_ratio",
        "mth1_ind1_ratio",
        "mth_ind1_ratio_dif",
        "mth_mtdcolrate_m1",
        "mth_mtdcolrate_m1_dif",
        "mth_mtdcolrate_m1new",
        "mth_mtdcolrate_m1new_dif",
        "mth_mtdcolrate_m1old",
        "mth_mtdcolrate_m1old_dif",
        "mth_mtdcolrate_m2",
        "mth_mtdcolrate_m2_dif",
        "mth_mtdcolrate_m2m6",
    }
)

# 模板已出现但尚未在 calculate_data_params 中实现的占位符（发现后应编码并移入 IMPLEMENTED_TEXT_PARAMS）
PLANNED_M1_MTD_PARAMS: frozenset[str] = frozenset()

TEXT_PARAM_SPECS: dict[str, dict[str, str]] = {
    "mm": {
        "label": "报告生成日所在月份（整数）",
        "formula": "datetime.now().month",
        "source": "本机系统日期",
        "charts": "—",
        "status": "已实现",
    },
    "mm1": {
        "label": "上一自然月月份（整数）",
        "formula": "上月末日期的 month",
        "source": "本机系统日期",
        "charts": "—",
        "status": "已实现",
    },
    "mm2": {
        "label": "上上一自然月月份（整数）",
        "formula": "上上月末日期的 month",
        "source": "本机系统日期",
        "charts": "—",
        "status": "已实现",
    },
    "DD": {
        "label": "报告生成日「日」（整数）",
        "formula": "datetime.now().day",
        "source": "本机系统日期",
        "charts": "—",
        "status": "已实现",
    },
    "DD1": {
        "label": "昨天「日」（整数）",
        "formula": "(now - 1天).day",
        "source": "本机系统日期",
        "charts": "—",
        "status": "已实现",
    },
    "rate_prin_od": {
        "label": "M0 金额逾期率（当前月同期窗口）",
        "formula": "逾期本金 / 账单本金；当月 billing_date 在最新月且日号≤窗口；上月同期可比",
        "source": "data/m0_billing.json",
        "charts": "m0_principal_overdue_rate_monthly.png",
        "status": "已实现",
    },
    "rate_cnt_od": {
        "label": "M0 单量（订单数）逾期率",
        "formula": "同窗口下逾期订单数 / 账单订单数",
        "source": "data/m0_billing.json",
        "charts": "m0_count_overdue_rate_monthly.png",
        "status": "已实现",
    },
    "rate_prin_od_dif": {
        "label": "金额逾期率环比差（百分点数值，非百分号）",
        "formula": "(本月同期 rate_prin_od - 上月同期 rate_prin_od) × 100",
        "source": "data/m0_billing.json",
        "charts": "同上金额逾期月图",
        "status": "已实现",
    },
    "rate_cnt_od_dif": {
        "label": "单量逾期率环比差（百分点数值）",
        "formula": "(本月同期 rate_cnt_od - 上月同期 rate_cnt_od) × 100",
        "source": "data/m0_billing.json",
        "charts": "同上单量逾期月图",
        "status": "已实现",
    },
    "wk_colrate7d": {
        "label": "M0 周度金额催回率（7d）最近成熟周",
        "formula": "(pd1-pd8)/pd1×100%；周日为周起始；week_end+8≤fetch",
        "source": "data/m0_billing.json",
        "charts": "m0_collection_rate_weekly.png",
        "status": "已实现",
    },
    "wk_colrate7d_dif": {
        "label": "周度 7d 催回率与上一成熟周差（百分点）",
        "formula": "最近成熟周 - 上一成熟周",
        "source": "data/m0_billing.json",
        "charts": "m0_collection_rate_weekly.png",
        "status": "已实现",
    },
    "wk_colrate15d": {
        "label": "M0 周度金额催回率（约 15d，pd16）最近成熟周",
        "formula": "(pd1-pd16)/pd1×100%；week_end+16≤fetch",
        "source": "data/m0_billing.json",
        "charts": "m0_collection_rate_weekly.png",
        "status": "已实现",
    },
    "wk_colrate15d_dif": {
        "label": "周度 15d 催回率与上一成熟周差（百分点）",
        "formula": "最近成熟周 - 上一成熟周",
        "source": "data/m0_billing.json",
        "charts": "m0_collection_rate_weekly.png",
        "status": "已实现",
    },
    "mth_colrate7d": {
        "label": "M0 月度金额催回率（7d）最近成熟月",
        "formula": "按月同期 cutoff（可与 screen_m0 回退一致）；账单≤fetch-8；(pd1-pd8)/pd1",
        "source": "data/m0_billing.json",
        "charts": "m0_collection_rate_7d_30d_monthly.png",
        "status": "已实现",
    },
    "mth_colrate7d_dif": {
        "label": "月度 7d 催回率与上一成熟月差（百分点）",
        "formula": "最近成熟月 - 上一成熟月",
        "source": "data/m0_billing.json",
        "charts": "m0_collection_rate_7d_30d_monthly.png",
        "status": "已实现",
    },
    "mth_colrate30d": {
        "label": "M0 月度金额催回率（30d）最近成熟月",
        "formula": "按月同期 cutoff；(pd1-pd31)/pd1；账单≤fetch-31",
        "source": "data/m0_billing.json",
        "charts": "m0_collection_rate_7d_30d_monthly.png",
        "status": "已实现",
    },
    "mth_colrate30d_dif": {
        "label": "月度 30d 催回率与上一成熟月差（百分点）",
        "formula": "最近成熟月 - 上一成熟月",
        "source": "data/m0_billing.json",
        "charts": "m0_collection_rate_7d_30d_monthly.png",
        "status": "已实现",
    },
    "mth_colrate7d_ind0": {
        "label": "非合并用户（IND0）月度 7d 催回率",
        "formula": "与 ind0 月图一致；cutoff 用 ctx（可回退）",
        "source": "data/m0_billing_grouped.json",
        "charts": "m0_collection_rate_7d_30d_monthly_ind0.png",
        "status": "已实现",
    },
    "mth_colrate7d_ind0_dif": {
        "label": "IND0 月 7d 催回率环比差（百分点）",
        "formula": "最近成熟月 - 上一成熟月",
        "source": "data/m0_billing_grouped.json",
        "charts": "m0_collection_rate_7d_30d_monthly_ind0.png",
        "status": "已实现",
    },
    "mth_colrate7d_ind1": {
        "label": "合并用户（IND1）月度 7d 催回率",
        "formula": "与 ind1 月图一致",
        "source": "data/m0_billing_grouped.json",
        "charts": "m0_collection_rate_7d_30d_monthly_ind1.png",
        "status": "已实现",
    },
    "mth_colrate7d_ind1_dif": {
        "label": "IND1 月 7d 催回率环比差（百分点）",
        "formula": "最近成熟月 - 上一成熟月",
        "source": "data/m0_billing_grouped.json",
        "charts": "m0_collection_rate_7d_30d_monthly_ind1.png",
        "status": "已实现",
    },
    "mth_ind1_ratio": {
        "label": "合并订单逾期金额占比（最新月桶）",
        "formula": "ind1_pastdue1d / (ind0+ind1)；月同期 cutoff 恒为 (fetch-1).day",
        "source": "data/m0_billing_grouped.json",
        "charts": "m0_ind1_ratio.png",
        "status": "已实现",
    },
    "mth1_ind1_ratio": {
        "label": "上一桶月份的 IND1 占比（用于环比文案）",
        "formula": "sorted(monthly_ind)[-2]",
        "source": "data/m0_billing_grouped.json",
        "charts": "m0_ind1_ratio.png",
        "status": "已实现",
    },
    "mth_ind1_ratio_dif": {
        "label": "IND1 占比环比差（百分点数值）",
        "formula": "最近月占比 - 上月占比",
        "source": "data/m0_billing_grouped.json",
        "charts": "m0_ind1_ratio.png",
        "status": "已实现",
    },
    "mth_mtdcolrate_m1": {
        "label": "M1 分案 MTD 累积回款率（整体）",
        "formula": "最新月最后一个 repaid 非空日：Σ回款/Σ分案本金（新+老）；与 assignment_repayment_overall 折线终点一致",
        "source": "data/m1_assignment_repayment.json",
        "charts": "assignment_repayment_overall.png",
        "status": "已实现",
    },
    "mth_mtdcolrate_m1_dif": {
        "label": "M1 整体 MTD 回款率环比（百分点）",
        "formula": "与整体相同号日率差；上月无同号则比上月末日",
        "source": "data/m1_assignment_repayment.json",
        "charts": "assignment_repayment_overall.png",
        "status": "已实现",
    },
    "mth_mtdcolrate_m1new": {
        "label": "M1 新案 MTD 累积回款率",
        "formula": "仅 case_type=新案；口径同 m1 图 new",
        "source": "data/m1_assignment_repayment.json",
        "charts": "assignment_repayment_new.png",
        "status": "已实现",
    },
    "mth_mtdcolrate_m1new_dif": {
        "label": "M1 新案 MTD 回款率环比（百分点）",
        "formula": "最近月 − 上一自然月 末日率",
        "source": "data/m1_assignment_repayment.json",
        "charts": "assignment_repayment_new.png",
        "status": "已实现",
    },
    "mth_mtdcolrate_m1old": {
        "label": "M1 老案 MTD 累积回款率",
        "formula": "仅 case_type=老案",
        "source": "data/m1_assignment_repayment.json",
        "charts": "assignment_repayment_old.png",
        "status": "已实现",
    },
    "mth_mtdcolrate_m1old_dif": {
        "label": "M1 老案 MTD 回款率环比（百分点）",
        "formula": "最近月 − 上一自然月 末日率",
        "source": "data/m1_assignment_repayment.json",
        "charts": "assignment_repayment_old.png",
        "status": "已实现",
    },
    "mth_mtdcolrate_m2": {
        "label": "M2 MTD 累积回款率（单类型 M2）",
        "formula": "按日累加 assigned+overdue_added 为分母、repaid 为分子得 cum_rate；取最新月最后一日",
        "source": "data/M2_class_all.json",
        "charts": "recovery_rate_M2_ALL.png",
        "status": "已实现",
    },
    "mth_mtdcolrate_m2_dif": {
        "label": "M2 MTD 回款率环比（百分点）",
        "formula": "最近月 − 上一自然月 cum_rate 末日差",
        "source": "data/M2_class_all.json",
        "charts": "recovery_rate_M2_ALL.png",
        "status": "已实现",
    },
    "mth_mtdcolrate_m2m6": {
        "label": "M2–M6（31–180 天）MTD 累积回款率",
        "formula": "同 screen_m2_m6 对 M6_class_all 的 cum_rate；取最新月最后一日",
        "source": "data/M6_class_all.json",
        "charts": "recovery_rate_M6_ALL.png",
        "status": "已实现",
    },
}

# 插图占位符 → 说明（key 为文件名）
PNG_PLACEHOLDER_SPECS: dict[str, dict[str, str]] = {
    "m0_principal_overdue_rate_monthly.png": {"desc": "M0 金额逾期率（月）", "params": "rate_prin_od, rate_prin_od_dif"},
    "m0_count_overdue_rate_monthly.png": {"desc": "M0 单量逾期率（月）", "params": "rate_cnt_od, rate_cnt_od_dif"},
    "m0_principal_overdue_rate_weekly.png": {"desc": "M0 金额逾期率（周）", "params": "—"},
    "m0_collection_rate_weekly.png": {"desc": "M0 周度催回（7d/15d）", "params": "wk_colrate7d, wk_colrate15d 及 *_dif"},
    "m0_collection_rate_7d_30d_monthly.png": {"desc": "M0 月度 7d/30d 催回", "params": "mth_colrate7d, mth_colrate30d 及 *_dif"},
    "m0_collection_rate_7d_30d_monthly_ind0.png": {"desc": "IND0 月 7d 催回", "params": "mth_colrate7d_ind0*"},
    "m0_collection_rate_7d_30d_monthly_ind1.png": {"desc": "IND1 月 7d 催回", "params": "mth_colrate7d_ind1*"},
    "m0_ind1_ratio.png": {"desc": "IND1 逾期金额占比（月）", "params": "mth_ind1_ratio*"},
    "assignment_repayment_overall.png": {"desc": "M1 分案回款·整体", "params": "mth_mtdcolrate_m1, mth_mtdcolrate_m1_dif"},
    "assignment_repayment_table_overall.png": {"desc": "M1 整体表", "params": "mth_mtdcolrate_m1*"},
    "assignment_repayment_new.png": {"desc": "M1·新案", "params": "mth_mtdcolrate_m1new*"},
    "assignment_repayment_table_new.png": {"desc": "M1 新案表", "params": "mth_mtdcolrate_m1new*"},
    "assignment_repayment_old.png": {"desc": "M1·老案", "params": "mth_mtdcolrate_m1old*"},
    "assignment_repayment_table_old.png": {"desc": "M1 老案表", "params": "mth_mtdcolrate_m1old*"},
    "recovery_rate_M2_ALL.png": {"desc": "M2 回款率", "params": "mth_mtdcolrate_m2*"},
    "recovery_rate_M2_table_ALL.png": {"desc": "M2 表", "params": "mth_mtdcolrate_m2*"},
    "recovery_rate_M6_ALL.png": {"desc": "M6 回款率", "params": "mth_mtdcolrate_m2m6"},
    "recovery_rate_M6_table_ALL.png": {"desc": "M6 表", "params": "mth_mtdcolrate_m2m6"},
    "avg_eff_worktime.png": {"desc": "人均有效工时", "params": "—"},
    "avg_eff_call_worktime.png": {"desc": "人均通话工时", "params": "—"},
    "avg_eff_wa_worktime.png": {"desc": "人均 WA 工时", "params": "—"},
    "case_stock_9grid.png": {"desc": "人均库存九宫格", "params": "—"},
    "full_call_full_rates.png": {"desc": "全量外呼满频等", "params": "—"},
    "full_call_avg_calls_per_case.png": {"desc": "案均拨打", "params": "—"},
    "full_call_eff_rates.png": {"desc": "有效外呼接通率等", "params": "—"},
    "full_call_avg_dur_per_case.png": {"desc": "案均有效通时", "params": "—"},
    "call_type_weekly_connect.png": {"desc": "拨打模式周接通率", "params": "—"},
    "precall_task_trends.png": {"desc": "预测试任务四指标", "params": "—"},
    "precall_afterkeep_trends.png": {"desc": "留案与留案后外呼三指标", "params": "—"},
    "recovery_rate_S_combined_ALL.png": {"desc": "S 类 ALL", "params": "—"},
    "recovery_rate_S_table_ALL.png": {"desc": "S ALL 表", "params": "—"},
    "recovery_rate_S_combined_NEW.png": {"desc": "S NEW", "params": "—"},
    "recovery_rate_S_table_NEW.png": {"desc": "S NEW 表", "params": "—"},
    "recovery_rate_S_combined_MTD.png": {"desc": "S MTD", "params": "—"},
    "recovery_rate_S_table_MTD.png": {"desc": "S MTD 表", "params": "—"},
    "grp_S1RA.png": {"desc": "GRP S1RA", "params": "—"},
    "grp_S1RC.png": {"desc": "GRP S1RC", "params": "—"},
    "grp_S2RA.png": {"desc": "GRP S2RA", "params": "—"},
    "grp_S2RC.png": {"desc": "GRP S2RC", "params": "—"},
    "grp_S3.png": {"desc": "GRP S3", "params": "—"},
}


def spec_status(key: str) -> str:
    if key in IMPLEMENTED_TEXT_PARAMS:
        return "已实现"
    if key in PLANNED_M1_MTD_PARAMS:
        return "待实现"
    return "未注册"


def merge_spec_row(key: str) -> dict[str, str]:
    base = TEXT_PARAM_SPECS.get(key)
    if base:
        out = dict(base)
        out.setdefault("status", spec_status(key))
        return out
    return {
        "label": "（脚本未登记含义）",
        "formula": "—",
        "source": "—",
        "charts": "—",
        "status": "未注册",
    }
