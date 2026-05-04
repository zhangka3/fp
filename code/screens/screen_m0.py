"""
生成M0逾期相关图表
数据源: ../../data/m0_billing.json, m0_billing_grouped.json（与 run_all 落盘文件名一致）
输出: 8张图表
"""
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timedelta

import chart_theme

chart_theme.apply_chart_theme()
font_prop = chart_theme.font_prop_dengxian()

# 数据和输出目录
DATA_DIR = Path(__file__).parent.parent.parent / 'data'
OUTPUT_DIR = Path(__file__).parent.parent.parent / 'screenshots'
OUTPUT_DIR.mkdir(exist_ok=True)


def load_m0_data():
    """
    加载M0月度数据（不过滤，返回所有数据和数据获取日期）

    优先从metadata读取数据获取时间，如果没有则推断
    返回: (rows, data_fetch_date)
    """
    filename = DATA_DIR / 'm0_billing.json'
    with open(filename, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    all_rows = json_data['rows']

    # 优先从metadata读取数据获取时间
    if 'metadata' in json_data and 'data_fetch_date' in json_data['metadata']:
        data_fetch_date_str = json_data['metadata']['data_fetch_date']
        data_fetch_date = datetime.strptime(data_fetch_date_str, '%Y-%m-%d')
        print(f"  加载 {filename.name}: {len(all_rows)} 行")
        print(f"  数据获取时间（从metadata读取）: {data_fetch_date_str}")
    else:
        # 兼容旧数据：通过推断最后一个principal_pastdue_1d > 0的日期
        last_valid_date = None
        for row in sorted(all_rows, key=lambda x: x[0], reverse=True):
            if float(row[4]) > 0:  # principal_pastdue_1d > 0
                last_valid_date = row[0]
                break

        if last_valid_date is None:
            raise ValueError("无法找到有效的逾期数据！")

        # 数据获取时间 = 最后有效日期 + 1天
        last_valid_dt = datetime.strptime(last_valid_date, '%Y-%m-%d')
        data_fetch_date = last_valid_dt + timedelta(days=1)

        print(f"  加载 {filename.name}: {len(all_rows)} 行")
        print(f"  最后有效逾期数据日期: {last_valid_date}")
        print(f"  推断数据获取时间: {data_fetch_date.strftime('%Y-%m-%d')}")

    return all_rows, data_fetch_date


def load_m0_grouped_data():
    """
    加载M0分组数据（按c_billing_user_overdue_ind）

    优先从metadata读取数据获取时间，如果没有则推断
    返回: (rows, data_fetch_date)
    """
    filename = DATA_DIR / 'm0_billing_grouped.json'
    with open(filename, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    rows = json_data['rows']

    # 优先从metadata读取数据获取时间
    if 'metadata' in json_data and 'data_fetch_date' in json_data['metadata']:
        data_fetch_date_str = json_data['metadata']['data_fetch_date']
        data_fetch_date = datetime.strptime(data_fetch_date_str, '%Y-%m-%d')
        print(f"  加载 {filename.name}: {len(rows)} 行")
        print(f"  数据获取时间（从metadata读取）: {data_fetch_date_str}")
    else:
        # 兼容旧数据：通过推断
        last_valid_date = None
        for row in sorted(rows, key=lambda x: x[0], reverse=True):
            if float(row[5]) > 0:  # principal_pastdue_1d > 0 (字段位置5)
                last_valid_date = row[0]
                break

        if last_valid_date is None:
            raise ValueError("分组数据：无法找到有效的逾期数据！")

        # 数据获取时间 = 最后有效日期 + 1天
        last_valid_dt = datetime.strptime(last_valid_date, '%Y-%m-%d')
        data_fetch_date = last_valid_dt + timedelta(days=1)

        print(f"  加载 {filename.name}: {len(rows)} 行")
        print(f"  推断数据获取时间: {data_fetch_date.strftime('%Y-%m-%d')}")

    return rows, data_fetch_date


def aggregate_weekly_data(rows, data_fetch_date, mature_days=1):
    """
    将每日数据聚合为周度数据（每周日为起始）

    参数:
        rows: 数据行
        data_fetch_date: 数据获取日期（推断出的）
        mature_days: 成熟天数（默认1天，用于逾期率）
    """
    from collections import defaultdict

    # 计算过滤截止日期：数据获取日期 - 成熟天数
    filter_date = (data_fetch_date - timedelta(days=mature_days)).strftime('%Y-%m-%d')

    weekly_data = defaultdict(lambda: {
        'billing_principal': 0,
        'principal_pastdue_1d': 0,
        'principal_pastdue_2d': 0,
        'principal_pastdue_4d': 0,
        'principal_pastdue_8d': 0,
        'principal_pastdue_16d': 0,
        'principal_pastdue_31d': 0
    })

    for row in rows:
        # header: [billing_date, billing_instalment_cnt, instalment_cnt_pastdue_1d,
        #          billing_principal, principal_pastdue_1d, ..., principal_pastdue_31d]
        billing_date = row[0]

        # 过滤未成熟的天数
        if billing_date > filter_date:
            continue

        date_obj = datetime.strptime(billing_date, '%Y-%m-%d')

        # 找到该日期所属的周日（周起始日）
        days_since_sunday = (date_obj.weekday() + 1) % 7  # 周日=0
        week_start = date_obj - timedelta(days=days_since_sunday)
        week_key = week_start.strftime('%Y-%m-%d')

        # 累加数据
        weekly_data[week_key]['billing_principal'] += float(row[3])
        weekly_data[week_key]['principal_pastdue_1d'] += float(row[4])
        weekly_data[week_key]['principal_pastdue_2d'] += float(row[5])
        weekly_data[week_key]['principal_pastdue_4d'] += float(row[6])
        weekly_data[week_key]['principal_pastdue_8d'] += float(row[8])
        weekly_data[week_key]['principal_pastdue_16d'] += float(row[12])
        weekly_data[week_key]['principal_pastdue_31d'] += float(row[13])

    return weekly_data


def aggregate_monthly_data(rows, data_fetch_date, mature_days=0, same_period=False):
    """
    将每日数据聚合为月度数据（每月1号）

    参数:
        rows: 数据行
        data_fetch_date: 数据获取日期（推断出的）
        mature_days: 成熟天数要求（0=不过滤, 1=逾期1d成熟, 8=7d催回成熟, 31=30d催回成熟）
        same_period: 是否同期对比（True=所有月份都只统计到月内相同日期）
    """
    from collections import defaultdict

    # 计算月内截止日期（用于同期对比）
    # 例：data_fetch_date=04-20, mature_days=1 → 月内截止日期=19号
    month_day_cutoff = (data_fetch_date - timedelta(days=mature_days)).day

    monthly_data = defaultdict(lambda: {
        'billing_instalment_cnt': 0,
        'instalment_cnt_pastdue_1d': 0,
        'billing_principal': 0,
        'principal_pastdue_1d': 0,
        'principal_pastdue_8d': 0,
        'principal_pastdue_31d': 0
    })

    for row in rows:
        billing_date = row[0]
        date_obj = datetime.strptime(billing_date, '%Y-%m-%d')

        # 同期对比：所有月份都只统计到月内相同日期
        if same_period:
            # 例如：如果month_day_cutoff=19，则只取每月1-19号的数据
            if date_obj.day > month_day_cutoff:
                continue
        else:
            # 非同期：只过滤最新月份的未成熟数据
            filter_date = (data_fetch_date - timedelta(days=mature_days)).strftime('%Y-%m-%d')
            if billing_date > filter_date:
                continue

        month_key = billing_date[:7]  # '2026-04'

        # 累加数据
        monthly_data[month_key]['billing_instalment_cnt'] += int(row[1])
        monthly_data[month_key]['instalment_cnt_pastdue_1d'] += int(row[2])
        monthly_data[month_key]['billing_principal'] += float(row[3])
        monthly_data[month_key]['principal_pastdue_1d'] += float(row[4])
        monthly_data[month_key]['principal_pastdue_8d'] += float(row[8])
        monthly_data[month_key]['principal_pastdue_31d'] += float(row[13])

    return monthly_data


def generate_monthly_principal_overdue_rate(monthly_data):
    """1. 金额逾期率（by月同期）"""
    months = sorted(monthly_data.keys())
    month_labels = [f"{m[5:7]}.01" for m in months]
    principals = []
    overdue_rates = []

    for month in months:
        data = monthly_data[month]
        principal = data['billing_principal']
        overdue_1d = data['principal_pastdue_1d']

        principals.append(principal / 1e6)
        if principal > 0:
            overdue_rates.append((overdue_1d / principal) * 100)
        else:
            overdue_rates.append(0)

    fig, ax1 = plt.subplots(figsize=(21, 12), dpi=100)

    # 柱状图：到期金额
    x = np.arange(len(months))
    bars = ax1.bar(x, principals, width=0.6, color=chart_theme.M0_VOLUME_BAR, alpha=0.90, edgecolor='#FFFFFF', linewidth=0.4)
    ax1.set_xlabel('月份', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.set_ylabel('到期金额（百万）', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.tick_params(axis='y', labelsize=10)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:,.0f}'))
    ax1.set_xticks(x)
    ax1.set_xticklabels(month_labels, fontproperties=font_prop, fontsize=13, rotation=45)

    # 折线图：逾期率
    ax2 = ax1.twinx()
    line = ax2.plot(x, overdue_rates, color=chart_theme.M0_OVERDUE_LINE, linewidth=2.5, marker='o', markersize=6)
    ax2.set_ylabel('金额逾期率 (%)', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax2.tick_params(axis='y', labelsize=10)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}%'))

    # 标注所有点的逾期率
    for i, rate in enumerate(overdue_rates):
        ax2.annotate(f'{rate:.2f}%',
                    xy=(i, rate),
                    xytext=(0, 8),
                    textcoords='offset points',
                    fontsize=15,
                    fontweight='bold',
                    color=chart_theme.TEXT_PRIMARY,
                    ha='center',
                    fontproperties=font_prop)

    # 设置y轴范围
    max_rate = max(overdue_rates) if overdue_rates else 100
    ax2.set_ylim(bottom=0, top=max_rate * 1.15)

    chart_theme.polish_twin_bars_and_lines(ax1, ax2, stacked_bars=False)

    fig.suptitle('M0金额逾期率（按月同期）', fontsize=24, fontweight='bold', fontproperties=font_prop, y=0.98, color=chart_theme.TEXT_PRIMARY)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_path = OUTPUT_DIR / 'm0_principal_overdue_rate_monthly.png'
    chart_theme.save_figure(fig, output_path, dpi=150)
    plt.close()

    print(f'  OK: {output_path.name}')


def generate_monthly_count_overdue_rate(monthly_data):
    """2. 单量逾期率（by月同期）"""
    months = sorted(monthly_data.keys())
    month_labels = [f"{m[5:7]}.01" for m in months]
    counts = []
    overdue_rates = []

    for month in months:
        data = monthly_data[month]
        cnt = data['billing_instalment_cnt']
        overdue_cnt = data['instalment_cnt_pastdue_1d']

        counts.append(cnt)
        if cnt > 0:
            overdue_rates.append((overdue_cnt / cnt) * 100)
        else:
            overdue_rates.append(0)

    fig, ax1 = plt.subplots(figsize=(21, 12), dpi=100)

    x = np.arange(len(months))
    bars = ax1.bar(x, counts, width=0.6, color=chart_theme.M0_BAR_ALT, alpha=0.90, edgecolor='#FFFFFF', linewidth=0.4)
    ax1.set_xlabel('月份', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.set_ylabel('到期账单量', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.tick_params(axis='y', labelsize=10)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:,.0f}'))
    ax1.set_xticks(x)
    ax1.set_xticklabels(month_labels, fontproperties=font_prop, fontsize=13, rotation=45)

    ax2 = ax1.twinx()
    line = ax2.plot(x, overdue_rates, color=chart_theme.M0_COUNT_LINE, linewidth=2.5, marker='o', markersize=6)
    ax2.set_ylabel('单量逾期率 (%)', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax2.tick_params(axis='y', labelsize=10)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}%'))

    # 标注所有点的逾期率
    for i, rate in enumerate(overdue_rates):
        ax2.annotate(f'{rate:.2f}%',
                    xy=(i, rate),
                    xytext=(0, 8),
                    textcoords='offset points',
                    fontsize=15,
                    fontweight='bold',
                    color=chart_theme.TEXT_PRIMARY,
                    ha='center',
                    fontproperties=font_prop)

    # 设置y轴范围
    max_rate = max(overdue_rates) if overdue_rates else 100
    ax2.set_ylim(bottom=0, top=max_rate * 1.15)

    chart_theme.polish_twin_bars_and_lines(ax1, ax2, stacked_bars=False)

    fig.suptitle('M0单量逾期率（按月同期）', fontsize=24, fontweight='bold', fontproperties=font_prop, y=0.98, color=chart_theme.TEXT_PRIMARY)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_path = OUTPUT_DIR / 'm0_count_overdue_rate_monthly.png'
    chart_theme.save_figure(fig, output_path, dpi=150)
    plt.close()

    print(f'  OK: {output_path.name}')


def generate_weekly_principal_overdue_rate(weekly_data):
    """3. 金额逾期率（by周）"""
    weeks = sorted(weekly_data.keys())[-12:]  # 只取最近12周
    # 横坐标显示：周日起始日，格式 MM.DD
    week_labels = [f"{w[5:7]}.{w[8:10]}" for w in weeks]
    principals = []
    overdue_rates = []

    for week in weeks:
        data = weekly_data[week]
        principal = data['billing_principal']
        overdue_1d = data['principal_pastdue_1d']

        principals.append(principal / 1e6)
        if principal > 0:
            overdue_rates.append((overdue_1d / principal) * 100)
        else:
            overdue_rates.append(0)

    fig, ax1 = plt.subplots(figsize=(21, 12), dpi=100)

    x = np.arange(len(weeks))
    bars = ax1.bar(x, principals, width=0.6, color=chart_theme.M0_VOLUME_BAR, alpha=0.90, edgecolor='#FFFFFF', linewidth=0.4)
    ax1.set_xlabel('周起始日期', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.set_ylabel('到期金额（百万）', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.tick_params(axis='y', labelsize=10)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:,.0f}'))
    ax1.set_xticks(x)
    ax1.set_xticklabels(week_labels, fontproperties=font_prop, fontsize=12, rotation=45)

    ax2 = ax1.twinx()
    line = ax2.plot(x, overdue_rates, color=chart_theme.M0_OVERDUE_LINE, linewidth=2.5, marker='o', markersize=6)
    ax2.set_ylabel('金额逾期率 (%)', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax2.tick_params(axis='y', labelsize=10)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}%'))

    # 标注所有点
    for i, rate in enumerate(overdue_rates):
        ax2.annotate(f'{rate:.2f}%',
                    xy=(i, rate),
                    xytext=(0, 8),
                    textcoords='offset points',
                    fontsize=14,
                    fontweight='bold',
                    color=chart_theme.TEXT_PRIMARY,
                    ha='center',
                    fontproperties=font_prop)

    max_rate = max(overdue_rates) if overdue_rates else 100
    ax2.set_ylim(bottom=0, top=max_rate * 1.15)

    chart_theme.polish_twin_bars_and_lines(ax1, ax2, stacked_bars=False)

    fig.suptitle('M0金额逾期率（按周）', fontsize=24, fontweight='bold', fontproperties=font_prop, y=0.98, color=chart_theme.TEXT_PRIMARY)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_path = OUTPUT_DIR / 'm0_principal_overdue_rate_weekly.png'
    chart_theme.save_figure(fig, output_path, dpi=150)
    plt.close()

    print(f'  OK: {output_path.name}')


def generate_weekly_collection_rate(weekly_data, data_fetch_date):
    """
    4. 金额催回率（by周）- 1d/3d/7d/15d/30d

    催回率需要不同的成熟期，在weekly_data基础上进一步判断
    """
    weeks = sorted(weekly_data.keys())[-12:]  # 只取最近12周
    week_labels = [f"{w[5:7]}.{w[8:10]}" for w in weeks]
    principals = []
    collection_rates = {
        '1d': [], '3d': [], '7d': [], '15d': [], '30d': []
    }

    for week in weeks:
        data = weekly_data[week]
        principal = data['billing_principal']
        pastdue_1d = data['principal_pastdue_1d']
        pastdue_2d = data['principal_pastdue_2d']
        pastdue_4d = data['principal_pastdue_4d']
        pastdue_8d = data['principal_pastdue_8d']
        pastdue_16d = data['principal_pastdue_16d']
        pastdue_31d = data['principal_pastdue_31d']

        principals.append(principal / 1e6)

        # 解析周起始日期
        week_start = datetime.strptime(week, '%Y-%m-%d').date()
        week_end = week_start + timedelta(days=6)

        # 成熟度检查：周末最后一天的账单需要等N天后才能看到N天催回率
        # data_fetch_date是数据获取时间，week_end + N天 < data_fetch_date 才成熟
        if pastdue_1d > 0 and week_end + timedelta(days=2) < data_fetch_date.date():
            collection_rates['1d'].append(((pastdue_1d - pastdue_2d) / pastdue_1d) * 100)
        else:
            collection_rates['1d'].append(None)

        if pastdue_1d > 0 and week_end + timedelta(days=4) < data_fetch_date.date():
            collection_rates['3d'].append(((pastdue_1d - pastdue_4d) / pastdue_1d) * 100)
        else:
            collection_rates['3d'].append(None)

        if pastdue_1d > 0 and week_end + timedelta(days=8) < data_fetch_date.date():
            collection_rates['7d'].append(((pastdue_1d - pastdue_8d) / pastdue_1d) * 100)
        else:
            collection_rates['7d'].append(None)

        if pastdue_1d > 0 and week_end + timedelta(days=16) < data_fetch_date.date():
            collection_rates['15d'].append(((pastdue_1d - pastdue_16d) / pastdue_1d) * 100)
        else:
            collection_rates['15d'].append(None)

        if pastdue_1d > 0 and week_end + timedelta(days=31) < data_fetch_date.date():
            collection_rates['30d'].append(((pastdue_1d - pastdue_31d) / pastdue_1d) * 100)
        else:
            collection_rates['30d'].append(None)

    fig, ax1 = plt.subplots(figsize=(21, 12), dpi=100)

    x = np.arange(len(weeks))
    bars = ax1.bar(x, principals, width=0.6, color=chart_theme.M0_VOLUME_BAR, alpha=0.90, edgecolor='#FFFFFF', linewidth=0.4)
    ax1.set_xlabel('周起始日期', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.set_ylabel('到期金额（百万）', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.tick_params(axis='y', labelsize=10)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:,.0f}'))
    ax1.set_xticks(x)
    ax1.set_xticklabels(week_labels, fontproperties=font_prop, fontsize=12, rotation=45)

    ax2 = ax1.twinx()

    colors = dict(chart_theme.M0_WEEKLY_LINE_MAP)

    # 绘制每条线
    for period, rates in collection_rates.items():
        valid_indices = [i for i, r in enumerate(rates) if r is not None]
        valid_x = [x[i] for i in valid_indices]
        valid_rates = [rates[i] for i in valid_indices]

        if valid_rates:
            ax2.plot(valid_x, valid_rates, color=colors[period], linewidth=2,
                    marker='o', markersize=5, label=f'{period}催回率', alpha=0.9)

            # 标注最后5个有效点
            num_points_to_annotate = min(5, len(valid_rates))
            for idx in range(len(valid_rates) - num_points_to_annotate, len(valid_rates)):
                ax2.annotate(f'{valid_rates[idx]:.2f}%',
                            xy=(valid_x[idx], valid_rates[idx]),
                            xytext=(8, 5),
                            textcoords='offset points',
                            fontsize=13,
                            fontweight='bold',
                            color=chart_theme.TEXT_PRIMARY,
                            fontproperties=font_prop)

    ax2.set_ylabel('金额催回率 (%)', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax2.tick_params(axis='y', labelsize=10)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0f}%'))

    # 设置y轴范围
    all_rates = [r for rates in collection_rates.values() for r in rates if r is not None]
    if all_rates:
        max_rate = max(all_rates)
        ax2.set_ylim(bottom=0, top=max_rate * 1.15)

    ax2.legend(loc='upper left', fontsize=10, prop=font_prop)

    chart_theme.polish_twin_bars_and_lines(ax1, ax2, stacked_bars=False)

    fig.suptitle('M0金额催回率（按周）', fontsize=24, fontweight='bold', fontproperties=font_prop, y=0.98, color=chart_theme.TEXT_PRIMARY)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_path = OUTPUT_DIR / 'm0_collection_rate_weekly.png'
    chart_theme.save_figure(fig, output_path, dpi=150)
    plt.close()

    print(f'  OK: {output_path.name}')


def generate_monthly_collection_rate_7d_30d(rows, data_fetch_date):
    """
    5. 7d/30d催回率（by月同期）

    重要：确保7d和30d回款率使用各自成熟的数据，且月同期对比
    - 7d: 使用 billing_date <= data_fetch_date - 8 的数据
    - 30d: 使用 billing_date <= data_fetch_date - 31 的数据
    - 月同期：所有月份都只统计到月内相同日期
    """
    # 分别聚合7d和30d成熟的数据，启用月同期对比
    monthly_data_7d = aggregate_monthly_data(rows, data_fetch_date, mature_days=8, same_period=True)
    monthly_data_30d = aggregate_monthly_data(rows, data_fetch_date, mature_days=31, same_period=True)
    monthly_data_all = aggregate_monthly_data(rows, data_fetch_date, mature_days=0, same_period=True)

    # 获取所有月份
    all_months = set(monthly_data_7d.keys()) | set(monthly_data_30d.keys()) | set(monthly_data_all.keys())
    months = sorted(all_months)
    month_labels = [f"{m[5:7]}.01" for m in months]
    principals = []
    collection_rates_7d = []
    collection_rates_30d = []

    for month in months:
        # 用全部数据的principal作为柱状图
        data_all = monthly_data_all.get(month, {})
        principal = data_all.get('billing_principal', 0)
        principals.append(principal / 1e6)

        # 7d回款率：使用7d成熟的数据
        data_7d = monthly_data_7d.get(month, {})
        overdue_1d_7d = data_7d.get('principal_pastdue_1d', 0)
        overdue_8d_7d = data_7d.get('principal_pastdue_8d', 0)

        if overdue_1d_7d > 0:
            collection_rates_7d.append(((overdue_1d_7d - overdue_8d_7d) / overdue_1d_7d) * 100)
        else:
            collection_rates_7d.append(None)

        # 30d回款率：使用30d成熟的数据
        data_30d = monthly_data_30d.get(month, {})
        overdue_1d_30d = data_30d.get('principal_pastdue_1d', 0)
        overdue_31d_30d = data_30d.get('principal_pastdue_31d', 0)

        if overdue_1d_30d > 0 and overdue_31d_30d > 0:
            collection_rates_30d.append(((overdue_1d_30d - overdue_31d_30d) / overdue_1d_30d) * 100)
        else:
            collection_rates_30d.append(None)

    fig, ax1 = plt.subplots(figsize=(21, 12), dpi=100)

    x = np.arange(len(months))
    bars = ax1.bar(x, principals, width=0.6, color=chart_theme.M0_VOLUME_BAR, alpha=0.90, edgecolor='#FFFFFF', linewidth=0.4)
    ax1.set_xlabel('月份', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.set_ylabel('到期金额（百万）', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.tick_params(axis='y', labelsize=10)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:,.0f}'))
    ax1.set_xticks(x)
    ax1.set_xticklabels(month_labels, fontproperties=font_prop, fontsize=13, rotation=45)

    ax2 = ax1.twinx()

    # 绘制7d催回率
    valid_7d_indices = [i for i, r in enumerate(collection_rates_7d) if r is not None]
    if valid_7d_indices:
        valid_7d_x = [x[i] for i in valid_7d_indices]
        valid_7d_rates = [collection_rates_7d[i] for i in valid_7d_indices]
        ax2.plot(valid_7d_x, valid_7d_rates, color=chart_theme.M0_COLLECTION_7D, linewidth=2.5, marker='o', markersize=6,
                label='7d催回率', alpha=0.9)

    # 绘制30d催回率
    valid_30d_indices = [i for i, r in enumerate(collection_rates_30d) if r is not None]
    if valid_30d_indices:
        valid_30d_x = [x[i] for i in valid_30d_indices]
        valid_30d_rates = [collection_rates_30d[i] for i in valid_30d_indices]
        ax2.plot(valid_30d_x, valid_30d_rates, color=chart_theme.M0_COLLECTION_30D, linewidth=2.5, marker='s', markersize=6,
                label='30d催回率', alpha=0.9)

    # 智能标注
    if valid_7d_indices and valid_30d_indices:
        common_x = set(valid_7d_x) & set(valid_30d_x)

        for i in valid_7d_x:
            rate_7d = valid_7d_rates[valid_7d_x.index(i)]
            if i in common_x:
                rate_30d = valid_30d_rates[valid_30d_x.index(i)]
                offset_7d = (0, 12) if rate_7d > rate_30d + 2 else (0, -18)
            else:
                offset_7d = (0, 12)

            ax2.annotate(f'{rate_7d:.2f}%',
                        xy=(i, rate_7d),
                        xytext=offset_7d,
                        textcoords='offset points',
                        fontsize=14,
                        fontweight='bold',
                        color=chart_theme.TEXT_PRIMARY,
                        ha='center',
                        fontproperties=font_prop)

        for i in valid_30d_x:
            rate_30d = valid_30d_rates[valid_30d_x.index(i)]
            if i in common_x:
                rate_7d = valid_7d_rates[valid_7d_x.index(i)]
                offset_30d = (0, 12) if rate_30d > rate_7d + 2 else (0, -18)
            else:
                offset_30d = (0, 12)

            ax2.annotate(f'{rate_30d:.2f}%',
                        xy=(i, rate_30d),
                        xytext=offset_30d,
                        textcoords='offset points',
                        fontsize=14,
                        fontweight='bold',
                        color=chart_theme.TEXT_PRIMARY,
                        ha='center',
                        fontproperties=font_prop)

    ax2.set_ylabel('金额催回率 (%)', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax2.tick_params(axis='y', labelsize=10)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0f}%'))

    # 设置y轴范围
    all_rates = [r for r in collection_rates_7d + collection_rates_30d if r is not None]
    if all_rates:
        max_rate = max(all_rates)
        ax2.set_ylim(bottom=0, top=max_rate * 1.15)

    ax2.legend(loc='upper left', fontsize=10, prop=font_prop)

    chart_theme.polish_twin_bars_and_lines(ax1, ax2, stacked_bars=False)

    fig.suptitle('M0金额催回率（7d/30d，按月同期）', fontsize=24, fontweight='bold', fontproperties=font_prop, y=0.98, color=chart_theme.TEXT_PRIMARY)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_path = OUTPUT_DIR / 'm0_collection_rate_7d_30d_monthly.png'
    chart_theme.save_figure(fig, output_path, dpi=150)
    plt.close()

    print(f'  OK: {output_path.name}')


def generate_ind_ratio_chart(grouped_rows, data_fetch_date):
    """
    6. IND1占比图（M0逾期用户中合并订单用户占比，按月同期）

    逾期1d数据需要1天成熟期，且月同期对比
    """
    from collections import defaultdict

    # 计算月内截止日期：数据获取日期 - 1天
    month_day_cutoff = (data_fetch_date - timedelta(days=1)).day

    monthly_ind = defaultdict(lambda: {'ind0': 0, 'ind1': 0})

    for row in grouped_rows:
        # header: [billing_date, c_billing_user_overdue_ind, ..., principal_pastdue_1d, ...]
        billing_date = row[0]
        date_obj = datetime.strptime(billing_date, '%Y-%m-%d')

        # 月同期：所有月份都只统计到月内相同日期
        if date_obj.day > month_day_cutoff:
            continue

        ind = row[1]  # '0' or '1'
        principal_pastdue_1d = float(row[5])

        month_key = billing_date[:7]

        if ind == '0':
            monthly_ind[month_key]['ind0'] += principal_pastdue_1d
        else:
            monthly_ind[month_key]['ind1'] += principal_pastdue_1d

    months = sorted(monthly_ind.keys())
    month_labels = [f"{m[5:7]}.01" for m in months]
    ind1_ratios = []

    for month in months:
        data = monthly_ind[month]
        total = data['ind0'] + data['ind1']
        if total > 0:
            ind1_ratios.append((data['ind1'] / total) * 100)
        else:
            ind1_ratios.append(0)

    fig, ax = plt.subplots(figsize=(21, 12), dpi=100)

    x = np.arange(len(months))
    line = ax.plot(x, ind1_ratios, color=chart_theme.M0_IND1_LINE, linewidth=2.5, marker='o', markersize=6)
    ax.set_xlabel('月份', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax.set_ylabel('IND1占比 (%)', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax.tick_params(axis='y', labelsize=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}%'))
    ax.set_xticks(x)
    ax.set_xticklabels(month_labels, fontproperties=font_prop, fontsize=13, rotation=45)

    # 标注所有点
    for i, ratio in enumerate(ind1_ratios):
        ax.annotate(f'{ratio:.2f}%',
                    xy=(i, ratio),
                    xytext=(0, 8),
                    textcoords='offset points',
                    fontsize=15,
                    fontweight='bold',
                    color=chart_theme.TEXT_PRIMARY,
                    ha='center',
                    fontproperties=font_prop)

    max_ratio = max(ind1_ratios) if ind1_ratios else 100
    ax.set_ylim(bottom=0, top=max_ratio * 1.15)

    chart_theme.polish_ax_lines(ax, stroke_extra=3.2)

    fig.suptitle('M0逾期金额中合并订单用户占比（按月）', fontsize=24, fontweight='bold', fontproperties=font_prop, y=0.98, color=chart_theme.TEXT_PRIMARY)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_path = OUTPUT_DIR / 'm0_ind1_ratio.png'
    chart_theme.save_figure(fig, output_path, dpi=150)
    plt.close()

    print(f'  OK: {output_path.name}')


def generate_ind_collection_rate_chart(grouped_rows, data_fetch_date):
    """
    7-8. IND0和IND1的7d/30d催回率（按月同期）

    重要：确保7d和30d回款率使用各自成熟的数据，且月同期对比
    """
    from collections import defaultdict

    # 计算月内截止日期（用于同期对比）
    month_day_cutoff_7d = (data_fetch_date - timedelta(days=8)).day
    month_day_cutoff_30d = (data_fetch_date - timedelta(days=31)).day

    # 按月和ind统计 - 分别处理7d和30d成熟数据
    monthly_ind_7d = defaultdict(lambda: defaultdict(lambda: {
        'principal_pastdue_1d': 0,
        'principal_pastdue_8d': 0
    }))
    monthly_ind_30d = defaultdict(lambda: defaultdict(lambda: {
        'principal_pastdue_1d': 0,
        'principal_pastdue_31d': 0
    }))
    monthly_ind_all = defaultdict(lambda: defaultdict(lambda: {
        'principal_pastdue_1d': 0
    }))

    for row in grouped_rows:
        billing_date = row[0]
        date_obj = datetime.strptime(billing_date, '%Y-%m-%d')
        ind = row[1]
        principal_pastdue_1d = float(row[5])
        principal_pastdue_8d = float(row[8])
        principal_pastdue_31d = float(row[14])

        month_key = billing_date[:7]

        # 全部数据（用于柱状图）- 月同期：只取每月1-19号（或其他截止日）
        if date_obj.day <= (data_fetch_date - timedelta(days=1)).day:
            monthly_ind_all[month_key][ind]['principal_pastdue_1d'] += principal_pastdue_1d

        # 7d成熟数据 - 月同期：只取每月1-12号（例如）
        if date_obj.day <= month_day_cutoff_7d:
            monthly_ind_7d[month_key][ind]['principal_pastdue_1d'] += principal_pastdue_1d
            monthly_ind_7d[month_key][ind]['principal_pastdue_8d'] += principal_pastdue_8d

        # 30d成熟数据 - 月同期
        if date_obj.day <= month_day_cutoff_30d:
            monthly_ind_30d[month_key][ind]['principal_pastdue_1d'] += principal_pastdue_1d
            monthly_ind_30d[month_key][ind]['principal_pastdue_31d'] += principal_pastdue_31d

    months = sorted(set(monthly_ind_all.keys()) | set(monthly_ind_7d.keys()) | set(monthly_ind_30d.keys()))

    # 生成两张图：ind0和ind1
    for ind_value in ['0', '1']:
        month_labels = [f"{m[5:7]}.01" for m in months]
        principals = []
        collection_rates_7d = []
        collection_rates_30d = []

        for month in months:
            # 用全部数据作为柱状图
            data_all = monthly_ind_all[month][ind_value]
            principals.append(data_all['principal_pastdue_1d'] / 1e6)

            # 7d回款率
            data_7d = monthly_ind_7d[month][ind_value]
            pastdue_1d_7d = data_7d.get('principal_pastdue_1d', 0)
            pastdue_8d_7d = data_7d.get('principal_pastdue_8d', 0)

            if pastdue_1d_7d > 0:
                collection_rates_7d.append(((pastdue_1d_7d - pastdue_8d_7d) / pastdue_1d_7d) * 100)
            else:
                collection_rates_7d.append(None)

            # 30d回款率
            data_30d = monthly_ind_30d[month][ind_value]
            pastdue_1d_30d = data_30d.get('principal_pastdue_1d', 0)
            pastdue_31d_30d = data_30d.get('principal_pastdue_31d', 0)

            if pastdue_1d_30d > 0 and pastdue_31d_30d > 0:
                collection_rates_30d.append(((pastdue_1d_30d - pastdue_31d_30d) / pastdue_1d_30d) * 100)
            else:
                collection_rates_30d.append(None)

        fig, ax1 = plt.subplots(figsize=(21, 12), dpi=100)

        x = np.arange(len(months))
        bars = ax1.bar(x, principals, width=0.6, color=chart_theme.M0_VOLUME_BAR, alpha=0.90, edgecolor='#FFFFFF', linewidth=0.4)
        ax1.set_xlabel('月份', fontsize=12, fontweight='bold', fontproperties=font_prop)
        ax1.set_ylabel('逾期金额（百万）', fontsize=12, fontweight='bold', fontproperties=font_prop)
        ax1.tick_params(axis='y', labelsize=10)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:,.0f}'))
        ax1.set_xticks(x)
        ax1.set_xticklabels(month_labels, fontproperties=font_prop, fontsize=13, rotation=45)

        ax2 = ax1.twinx()

        # 7d和30d催回率
        valid_7d = [i for i, r in enumerate(collection_rates_7d) if r is not None]
        if valid_7d:
            valid_7d_x = [x[i] for i in valid_7d]
            valid_7d_rates = [collection_rates_7d[i] for i in valid_7d]
            ax2.plot(valid_7d_x, valid_7d_rates, color=chart_theme.M0_COLLECTION_7D, linewidth=2.5, marker='o', markersize=6,
                    label='7d催回率', alpha=0.9)

        valid_30d = [i for i, r in enumerate(collection_rates_30d) if r is not None]
        if valid_30d:
            valid_30d_x = [x[i] for i in valid_30d]
            valid_30d_rates = [collection_rates_30d[i] for i in valid_30d]
            ax2.plot(valid_30d_x, valid_30d_rates, color=chart_theme.M0_COLLECTION_30D, linewidth=2.5, marker='s', markersize=6,
                    label='30d催回率', alpha=0.9)

        # 智能标注
        if valid_7d and valid_30d:
            common_x = set(valid_7d_x) & set(valid_30d_x)

            for i in valid_7d_x:
                rate_7d = valid_7d_rates[valid_7d_x.index(i)]
                if i in common_x:
                    rate_30d = valid_30d_rates[valid_30d_x.index(i)]
                    offset_7d = (0, 12) if rate_7d > rate_30d + 2 else (0, -18)
                else:
                    offset_7d = (0, 12)

                ax2.annotate(f'{rate_7d:.2f}%',
                            xy=(i, rate_7d),
                            xytext=offset_7d,
                            textcoords='offset points',
                            fontsize=14,
                            fontweight='bold',
                            color=chart_theme.TEXT_PRIMARY,
                            ha='center',
                            fontproperties=font_prop)

            for i in valid_30d_x:
                rate_30d = valid_30d_rates[valid_30d_x.index(i)]
                if i in common_x:
                    rate_7d = valid_7d_rates[valid_7d_x.index(i)]
                    offset_30d = (0, 12) if rate_30d > rate_7d + 2 else (0, -18)
                else:
                    offset_30d = (0, 12)

                ax2.annotate(f'{rate_30d:.2f}%',
                            xy=(i, rate_30d),
                            xytext=offset_30d,
                            textcoords='offset points',
                            fontsize=14,
                            fontweight='bold',
                            color=chart_theme.TEXT_PRIMARY,
                            ha='center',
                            fontproperties=font_prop)

        ax2.set_ylabel('金额催回率 (%)', fontsize=12, fontweight='bold', fontproperties=font_prop)
        ax2.tick_params(axis='y', labelsize=10)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0f}%'))

        all_rates = [r for r in collection_rates_7d + collection_rates_30d if r is not None]
        if all_rates:
            max_rate = max(all_rates)
            ax2.set_ylim(bottom=0, top=max_rate * 1.15)

        ax2.legend(loc='upper left', fontsize=10, prop=font_prop)

        chart_theme.polish_twin_bars_and_lines(ax1, ax2, stacked_bars=False)

        ind_label = '非合并订单用户' if ind_value == '0' else '合并订单用户'
        fig.suptitle(f'M0金额催回率（7d/30d，{ind_label}，按月同期）', fontsize=24, fontweight='bold', fontproperties=font_prop, y=0.98, color=chart_theme.TEXT_PRIMARY)
        plt.tight_layout(rect=[0, 0, 1, 0.96])

        output_path = OUTPUT_DIR / f'm0_collection_rate_7d_30d_monthly_ind{ind_value}.png'
        chart_theme.save_figure(fig, output_path, dpi=150)
        plt.close()

        print(f'  OK: {output_path.name}')


def main():
    """主函数：生成所有M0图表"""
    print("=" * 60)
    print("开始生成M0逾期相关图表...")
    print(f"数据目录: {DATA_DIR}")
    print(f"保存位置: {OUTPUT_DIR}")
    print("=" * 60)

    # 加载数据
    print("\n加载数据:")
    m0_rows, data_fetch_date = load_m0_data()
    m0_grouped_rows, data_fetch_date_grouped = load_m0_grouped_data()

    # 验证两个数据源的数据获取时间是否一致
    if data_fetch_date != data_fetch_date_grouped:
        print(f"  警告: 两个数据源的数据获取时间不一致!")
        print(f"    m0_billing.json: {data_fetch_date.strftime('%Y-%m-%d')}")
        print(f"    m0_billing_grouped.json: {data_fetch_date_grouped.strftime('%Y-%m-%d')}")

    # 聚合数据
    print("\n聚合数据:")
    # 逾期率需要1天成熟期（billing_date当天无法看到逾期1天情况）
    # 月同期：所有月份都只统计到月内相同日期
    monthly_data_overdue = aggregate_monthly_data(m0_rows, data_fetch_date, mature_days=1, same_period=True)
    weekly_data_overdue = aggregate_weekly_data(m0_rows, data_fetch_date, mature_days=1)
    # 催回率需要全部数据（成熟度在函数内部判断）
    weekly_data_collection = aggregate_weekly_data(m0_rows, data_fetch_date, mature_days=0)

    # 计算月内截止日期，用于输出日志
    month_day_cutoff = (data_fetch_date - timedelta(days=1)).day
    print(f"  月内截止日期: 每月{month_day_cutoff}号（用于月同期对比）")
    print(f"  月度数据（逾期率用）: {len(monthly_data_overdue)} 个月")
    print(f"  周度数据（逾期率用）: {len(weekly_data_overdue)} 周")
    print(f"  周度数据（催回率用）: {len(weekly_data_collection)} 周")

    # 生成图表
    print("\n生成图表:")
    generate_monthly_principal_overdue_rate(monthly_data_overdue)
    generate_monthly_count_overdue_rate(monthly_data_overdue)
    generate_weekly_principal_overdue_rate(weekly_data_overdue)
    generate_weekly_collection_rate(weekly_data_collection, data_fetch_date)
    generate_monthly_collection_rate_7d_30d(m0_rows, data_fetch_date)
    generate_ind_ratio_chart(m0_grouped_rows, data_fetch_date_grouped)
    generate_ind_collection_rate_chart(m0_grouped_rows, data_fetch_date_grouped)

    print("\n" + "=" * 60)
    print("M0图表生成完成！共 8 张图表")
    print("=" * 60)


if __name__ == '__main__':
    main()
