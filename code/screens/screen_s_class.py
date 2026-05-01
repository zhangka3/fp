"""
生成S类回款率图表
数据源: ../../data/s_class_all.json, s_class_new.json, s_class_mtd.json
输出: 15张图表 (S1/S2/S3 各3张 + S类组合图3张 + S类对比表3张)
"""
import json
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.ticker import FuncFormatter
from matplotlib import font_manager
from collections import defaultdict
import numpy as np
import os
from pathlib import Path

import chart_theme

chart_theme.apply_chart_theme()

# 数据和输出目录
DATA_DIR = Path(__file__).parent.parent.parent / 'data'
OUTPUT_DIR = Path(__file__).parent.parent.parent / 'screenshots'
OUTPUT_DIR.mkdir(exist_ok=True)


def load_data(assign_type):
    """
    加载指定类型的数据
    assign_type: 'all', 'new', 'mtd'
    """
    filename = DATA_DIR / f's_class_{assign_type}.json'
    with open(filename, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # 解析统一格式: {header, rows, rowCount}
    header = json_data['header']
    rows = json_data['rows']

    print(f"  加载 {filename.name}: {len(rows)} 行")
    return rows


def generate_single_chart(data, case_type, assign_type):
    """
    生成单个case_type的图表
    case_type: 'S1', 'S2', 'S3'
    assign_type: 'all', 'new', 'mtd'
    """
    type_label = {'all': '整体', 'new': '新案', 'mtd': '老案'}[assign_type]

    # 筛选数据
    filtered = [row for row in data if row[2] == case_type]

    if not filtered:
        print(f"  警告: {case_type} 没有数据")
        return

    # 按月份组织数据
    chart_data = defaultdict(lambda: {
        'days': [], 'assigned': [], 'overdue_added': [], 'repaid': [], 'rate': []
    })

    for row in filtered:
        # header: [p_month, day, case_type, assigned_principal, overdue_added_principal, repaid_principal]
        # rate is calculated as repaid / assigned
        p_month, day, ct, assigned, overdue_added, repaid = row
        day_num = int(day)
        
        # Calculate rate (回款率)
        assigned_val = float(assigned) if assigned else 0
        repaid_val = float(repaid) if repaid else 0
        rate = (repaid_val / assigned_val * 100) if assigned_val > 0 else 0

        chart_data[p_month]['days'].append(day_num)
        chart_data[p_month]['assigned'].append(assigned)
        chart_data[p_month]['overdue_added'].append(overdue_added)
        chart_data[p_month]['repaid'].append(repaid)
        chart_data[p_month]['rate'].append(rate)

    # 计算累积值
    for month in chart_data:
        days = chart_data[month]['days']
        assigned = chart_data[month]['assigned']
        overdue_added = chart_data[month]['overdue_added']
        repaid = chart_data[month]['repaid']

        # 排序
        sorted_indices = sorted(range(len(days)), key=lambda i: days[i])
        chart_data[month]['days'] = [days[i] for i in sorted_indices]
        chart_data[month]['assigned'] = [assigned[i] for i in sorted_indices]
        chart_data[month]['overdue_added'] = [overdue_added[i] for i in sorted_indices]
        chart_data[month]['repaid'] = [repaid[i] for i in sorted_indices]

        # 累积计算
        cum_assigned = []
        cum_overdue_added = []
        cum_repaid = []
        total_assigned = 0
        total_overdue_added = 0
        total_repaid = 0

        for i in range(len(chart_data[month]['days'])):
            total_assigned += float(chart_data[month]['assigned'][i])
            total_overdue_added += float(chart_data[month]['overdue_added'][i])
            total_repaid += float(chart_data[month]['repaid'][i])
            cum_assigned.append(total_assigned)
            cum_overdue_added.append(total_overdue_added)
            cum_repaid.append(total_repaid)

        # S类使用 assigned + overdue_added 作为分母
        cum_base = [cum_assigned[i] + cum_overdue_added[i] for i in range(len(cum_assigned))]

        # 转换为百万单位
        chart_data[month]['cum_assigned'] = [x / 1e6 for x in cum_base]
        chart_data[month]['cum_repaid'] = cum_repaid

        # 计算累积回款率
        cum_rate = []
        for i in range(len(cum_base)):
            if cum_base[i] > 0:
                cum_rate.append((cum_repaid[i] / cum_base[i]) * 100)
            else:
                cum_rate.append(0)
        chart_data[month]['cum_rate'] = cum_rate

    # 绘图 - 单张图，左轴bar右轴line
    fig, ax1 = plt.subplots(figsize=(14, 6))

    months = sorted(chart_data.keys())
    colors = chart_theme.month_color_dict(months)
    month_labels = {m: chart_theme.month_label_cn(m) for m in months}

    # 确定最大天数
    max_day = max([max(chart_data[m]['days']) for m in months])
    x_positions = list(range(1, max_day + 1))

    # === 左轴：堆叠bar（累积分案金额）===
    bottom_values = np.zeros(max_day)

    for month in months:
        data_month = chart_data[month]
        days = data_month['days']
        cum_assigned = data_month['cum_assigned']

        # 填充数据到完整的天数范围
        assigned_by_day = [0] * (max_day + 1)
        for j, day in enumerate(days):
            if day <= max_day:
                assigned_by_day[day] = cum_assigned[j]

        # 绘制堆叠bar
        ax1.bar(x_positions, assigned_by_day[1:],
               bottom=bottom_values,
               color=colors[month],
               alpha=0.85)

        bottom_values += np.array(assigned_by_day[1:])

    ax1.set_xlabel('天数', fontsize=12)
    ax1.set_ylabel('累积分案金额 (百万)', fontsize=12, color='black')
    ax1.tick_params(axis='y', labelcolor='black')

    # 格式化Y轴为带逗号的数字
    def format_millions(x, p):
        return f'{x:,.0f}'
    ax1.yaxis.set_major_formatter(FuncFormatter(format_millions))

    ax1.set_xlim(0.5, max_day + 0.5)
    ax1.set_xticks(range(1, max_day + 1))
    ax1.tick_params(axis='x', labelsize=8)
    chart_theme.style_axes_light(ax1, grid_axis='y')

    # === 右轴：累积回款率line ===
    ax2 = ax1.twinx()

    for month in months:
        data_month = chart_data[month]
        days = data_month['days']
        cum_rate = data_month['cum_rate']

        ax2.plot(days, cum_rate,
                marker='o', linewidth=2, markersize=4,
                label=f'{month_labels[month]}',
                color=colors[month])

        # 标注最后一个点（黑色加粗）
        if days:
            last_day = days[-1]
            last_rate = cum_rate[-1]
            ax2.plot(last_day, last_rate, 'o', color=chart_theme.LAST_POINT_MARKER, markersize=6, zorder=10)
            ax2.annotate(f'{last_rate:.2f}%',
                        xy=(last_day, last_rate),
                        xytext=(6, 6),
                        textcoords='offset points',
                        fontsize=9,
                        fontweight='bold',
                        color=chart_theme.ANNOTATE_COLOR)

    ax2.set_ylabel('累积回款率 (%)', fontsize=12, color='black')
    ax2.tick_params(axis='y', labelcolor='black')
    ax2.legend(loc='upper left', prop={'size': 10})

    chart_theme.polish_twin_bars_and_lines(ax1, ax2, stacked_bars=True)

    # 标题
    plt.title(f'{case_type} 累积回款率 ({type_label})', fontsize=14, fontweight='bold', pad=15)

    plt.tight_layout()

    # 保存到screenshots目录
    filename = OUTPUT_DIR / f'recovery_rate_{case_type}_{assign_type.upper()}.png'
    chart_theme.save_figure(fig, filename, dpi=150)
    plt.close()

    print(f"  OK: {filename.name}")


def generate_combined_chart(data, assign_type):
    """
    生成S1/S2/S3组合图
    assign_type: 'all', 'new', 'mtd'
    """
    type_label = {'all': '整体', 'new': '新案', 'mtd': '老案'}[assign_type]

    # 只保留S1/S2/S3
    filtered = [row for row in data if row[2] in ['S1', 'S2', 'S3']]

    # 组织数据：case_type -> month -> {days, cum_assigned, cum_rate}
    chart_data = defaultdict(lambda: defaultdict(lambda: {
        'days': [], 'assigned': [], 'overdue_added': [], 'repaid': []
    }))

    for row in filtered:
        p_month, day, case_type, assigned, overdue_added, repaid = row
        day_num = int(day)

        chart_data[case_type][p_month]['days'].append(day_num)
        chart_data[case_type][p_month]['assigned'].append(assigned)
        chart_data[case_type][p_month]['overdue_added'].append(overdue_added)
        chart_data[case_type][p_month]['repaid'].append(repaid)

    # 计算累积值
    for case_type in chart_data:
        for month in chart_data[case_type]:
            data_month = chart_data[case_type][month]
            days = data_month['days']
            assigned = data_month['assigned']
            overdue_added = data_month['overdue_added']
            repaid = data_month['repaid']

            # 排序
            sorted_indices = sorted(range(len(days)), key=lambda i: days[i])
            data_month['days'] = [days[i] for i in sorted_indices]
            data_month['assigned'] = [assigned[i] for i in sorted_indices]
            data_month['overdue_added'] = [overdue_added[i] for i in sorted_indices]
            data_month['repaid'] = [repaid[i] for i in sorted_indices]

            # 累积
            cum_assigned = []
            cum_overdue_added = []
            cum_repaid = []
            total_assigned = 0
            total_overdue_added = 0
            total_repaid = 0

            for i in range(len(data_month['days'])):
                total_assigned += float(data_month['assigned'][i])
                total_overdue_added += float(data_month['overdue_added'][i])
                total_repaid += float(data_month['repaid'][i])
                cum_assigned.append(total_assigned)
                cum_overdue_added.append(total_overdue_added)
                cum_repaid.append(total_repaid)

            # S类使用 assigned + overdue_added 作为分母
            cum_base = [cum_assigned[i] + cum_overdue_added[i] for i in range(len(cum_assigned))]

            data_month['cum_assigned'] = [v / 1e6 for v in cum_base]
            data_month['cum_repaid'] = cum_repaid

            # 累积回款率
            cum_rate = []
            for i in range(len(cum_base)):
                if cum_base[i] > 0:
                    cum_rate.append((cum_repaid[i] / cum_base[i]) * 100)
                else:
                    cum_rate.append(0)
            data_month['cum_rate'] = cum_rate

    # 绘图
    fig, axes = plt.subplots(3, 1, figsize=(16, 10))

    case_types = ['S1', 'S2', 'S3']
    months = sorted(chart_data[case_types[0]].keys())
    colors = chart_theme.month_color_dict(months)
    month_labels = {m: chart_theme.month_label_cn(m) for m in months}

    for idx, case_type in enumerate(case_types):
        ax1 = axes[idx]
        ax2 = ax1.twinx()

        # Bar: 累积分案金额
        bar_width = 0.2
        n_m = len(months)
        offsets = {m: (i - (n_m - 1) / 2) * bar_width for i, m in enumerate(months)}

        for month in months:
            if month not in chart_data[case_type]:
                continue

            data_month = chart_data[case_type][month]
            days = np.array(data_month['days'])
            cum_assigned = data_month['cum_assigned']

            ax1.bar(days + offsets[month], cum_assigned,
                   bar_width,
                   color=colors[month],
                   alpha=0.88,
                   edgecolor='#FFFFFF',
                   linewidth=0.45)

        ax1.set_ylabel('累积分案金额 (百万)', fontsize=11, fontweight='bold')
        ax1.tick_params(axis='y', labelsize=9)

        # 格式化Y轴
        def format_millions(x, p):
            return f'{x:,.0f}'
        ax1.yaxis.set_major_formatter(FuncFormatter(format_millions))

        # Line: 累积回款率
        for month in months:
            if month not in chart_data[case_type]:
                continue

            data_month = chart_data[case_type][month]
            days = data_month['days']
            cum_rate = data_month['cum_rate']

            ax2.plot(days, cum_rate,
                    color=colors[month],
                    linewidth=2,
                    marker='o',
                    markersize=4,
                    label=f'{month_labels[month]}',
                    alpha=1.0)

            # 标注最后一天（黑色加粗）
            if days:
                last_day = days[-1]
                last_rate = cum_rate[-1]
                ax2.plot(last_day, last_rate, 'o', color=chart_theme.LAST_POINT_MARKER, markersize=6, zorder=10)
                ax2.annotate(f'{last_rate:.2f}%',
                            xy=(last_day, last_rate),
                            xytext=(6, 6),
                            textcoords='offset points',
                            fontsize=9,
                            fontweight='bold',
                            color=chart_theme.ANNOTATE_COLOR)

        ax2.set_ylabel('累积回款率 (%)', fontsize=11, fontweight='bold')
        ax2.tick_params(axis='y', labelsize=9)

        # 标题
        ax1.set_title(f'{case_type} 月累积回款率 ({type_label})',
                     fontsize=13,
                     fontweight='bold',
                     pad=10)

        # X轴
        ax1.set_xlabel('天数', fontsize=10)
        ax1.set_xlim(0, 32)
        ax1.set_xticks(range(1, 32))
        ax1.set_xticklabels(range(1, 32))
        ax1.tick_params(axis='x', labelsize=8)
        chart_theme.style_axes_light(ax1, grid_axis='y')

        # 图例
        if idx == 0:
            ax2.legend(loc='upper left', frameon=True, fontsize=9)

        chart_theme.polish_twin_bars_and_lines(ax1, ax2, stacked_bars=False)

    plt.tight_layout()

    # 保存
    filename = OUTPUT_DIR / f'recovery_rate_S_combined_{assign_type.upper()}.png'
    chart_theme.save_figure(fig, filename, dpi=150)
    plt.close()

    print(f"  OK: {filename.name}")


def generate_table_chart(data, assign_type):
    """
    生成S1/S2/S3回款率对比表
    assign_type: 'all', 'new', 'mtd'
    """
    type_label = {'all': '整体', 'new': '新案', 'mtd': '老案'}[assign_type]

    # 只保留S1/S2/S3
    filtered = [row for row in data if row[2] in ['S1', 'S2', 'S3']]

    # 组织数据
    chart_data = defaultdict(lambda: defaultdict(lambda: {
        'days': [], 'assigned': [], 'overdue_added': [], 'repaid': []
    }))

    for row in filtered:
        p_month, day, case_type, assigned, overdue_added, repaid = row
        day_num = int(day)
        chart_data[case_type][p_month]['days'].append(day_num)
        chart_data[case_type][p_month]['assigned'].append(assigned)
        chart_data[case_type][p_month]['overdue_added'].append(overdue_added)
        chart_data[case_type][p_month]['repaid'].append(repaid)

    # 计算累积回款率
    for case_type in chart_data:
        for month in chart_data[case_type]:
            data_month = chart_data[case_type][month]
            days = data_month['days']
            assigned = data_month['assigned']
            overdue_added = data_month['overdue_added']
            repaid = data_month['repaid']

            # 排序
            sorted_indices = sorted(range(len(days)), key=lambda i: days[i])
            data_month['days'] = [days[i] for i in sorted_indices]
            data_month['assigned'] = [assigned[i] for i in sorted_indices]
            data_month['overdue_added'] = [overdue_added[i] for i in sorted_indices]
            data_month['repaid'] = [repaid[i] for i in sorted_indices]

            # 累积
            cum_assigned = []
            cum_overdue_added = []
            cum_repaid = []
            total_assigned = 0
            total_overdue_added = 0
            total_repaid = 0

            for i in range(len(data_month['days'])):
                total_assigned += float(data_month['assigned'][i])
                total_overdue_added += float(data_month['overdue_added'][i])
                total_repaid += float(data_month['repaid'][i])
                cum_assigned.append(total_assigned)
                cum_overdue_added.append(total_overdue_added)
                cum_repaid.append(total_repaid)

            # 累积回款率
            cum_rate = {}
            for i, day in enumerate(data_month['days']):
                cum_base = cum_assigned[i] + cum_overdue_added[i]
                if cum_base > 0:
                    cum_rate[day] = (cum_repaid[i] / cum_base) * 100
                else:
                    cum_rate[day] = 0
            data_month['cum_rate'] = cum_rate

    # 准备表格数据
    case_types = ['S1', 'S2', 'S3']
    _all_m = sorted({m for ct in chart_data for m in chart_data[ct]})
    months = _all_m[-3:]
    while len(months) < 3:
        months = [''] + months
    months = months[-3:]
    month_labels = {m: chart_theme.month_label_cn(m) if m else '' for m in months}

    # 构建表格数据
    table_data = []
    for day in range(1, 32):
        row = [str(day)]
        for case_type in case_types:
            for month in months:
                if month in chart_data[case_type]:
                    cum_rate_dict = chart_data[case_type][month]['cum_rate']
                    if day in cum_rate_dict:
                        rate = cum_rate_dict[day]
                        row.append(f"{rate:.2f}%")
                    else:
                        row.append("-")
                else:
                    row.append("-")
        table_data.append(row)

    # 创建图表（外圈浅底 + 表体留白，样式由 chart_theme 统一）
    fig, ax = plt.subplots(figsize=(14, 11))
    chart_theme.prepare_screen_table_figure(fig, ax)

    header_row1 = ['', '', 'S1', '', '', 'S2', '', '', 'S3', '']
    header_row2 = ['Day'] + [month_labels[m] for _ in case_types for m in months]

    full_table_data = [header_row1, header_row2] + table_data

    table = ax.table(
        cellText=full_table_data,
        cellLoc='center',
        loc='center',
        bbox=chart_theme.TABLE_AX_BBOX,
    )

    table.auto_set_font_size(False)
    font_prop = font_manager.FontProperties(family='DengXian')

    ncol = 10
    chart_theme.style_screen_table_s_headers(table, ncol=ncol, font_prop=font_prop)
    chart_theme.style_screen_table_body(
        table,
        data_row_start=2,
        nrows=len(full_table_data),
        ncol=ncol,
        font_prop=font_prop,
        day_col=0,
        percent_cols=frozenset(range(1, ncol)),
        data_fontsize=8,
    )

    chart_theme.set_screen_table_title(ax, f'S1/S2/S3 累积回款率对比表 ({type_label})')

    # 保存
    filename = OUTPUT_DIR / f'recovery_rate_S_table_{assign_type.upper()}.png'
    chart_theme.save_figure(
        fig,
        filename,
        dpi=150,
        save_facecolor=chart_theme.AXES_PANEL if chart_theme.VISUAL_STYLE == "dashboard" else chart_theme.FIG_FACE,
    )
    plt.close()

    print(f"  OK: {filename.name}")


def cleanup_old_charts(pattern):
    """清理旧图表文件"""
    old_files = list(OUTPUT_DIR.glob(pattern))
    if old_files:
        for f in old_files:
            f.unlink()
        print(f"[清除旧图表] {len(old_files)} 张\n")


def main():
    """主函数：生成所有S类图表"""
    types = ['all', 'new', 'mtd']
    case_types = ['S1', 'S2', 'S3']
    type_labels = {'all': '整体', 'new': '新案', 'mtd': '老案'}

    print("=" * 60)
    print("开始生成S类回款率图表...")
    print(f"数据目录: {DATA_DIR}")
    print(f"保存位置: {OUTPUT_DIR}")
    print("=" * 60)

    # 清除旧的S类图表
    cleanup_old_charts('recovery_rate_*.png')

    total_count = 0

    for assign_type in types:
        print(f"\n[{type_labels[assign_type]}]")

        # 加载数据
        data = load_data(assign_type)

        # 1. 生成每个case_type的单独图表 (9张)
        for case_type in case_types:
            generate_single_chart(data, case_type, assign_type)
            total_count += 1

        # 2. 生成组合图 (3张)
        generate_combined_chart(data, assign_type)
        total_count += 1

        # 3. 生成对比表 (3张)
        generate_table_chart(data, assign_type)
        total_count += 1

    print("\n" + "=" * 60)
    print(f"S类图表生成完成！共生成 {total_count} 张图表")
    print("=" * 60)


if __name__ == '__main__':
    main()
