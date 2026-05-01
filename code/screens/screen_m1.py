"""
生成M1分案回款图表
数据源: ../../data/m1_assignment_repayment.json
输出: 3 张柱线组合图 + 3 张纯表图（与 S 类 recovery_rate_S_table_* 风格一致）
"""
import calendar

import matplotlib.pyplot as plt
import matplotlib
import matplotlib.font_manager as font_manager
import numpy as np
import json
from pathlib import Path
from collections import defaultdict

import chart_theme

chart_theme.apply_chart_theme()
font_prop = chart_theme.font_prop_dengxian()

# 数据和输出目录
DATA_DIR = Path(__file__).parent.parent.parent / 'data'
OUTPUT_DIR = Path(__file__).parent.parent.parent / 'screenshots'
OUTPUT_DIR.mkdir(exist_ok=True)


def _days_in_month(ym: str) -> int:
    """ym 形如 YYYY-MM，返回该月实际天数。"""
    y, m = int(ym[:4]), int(ym[5:7])
    return calendar.monthrange(y, m)[1]


def load_data():
    """加载M1分案回款数据"""
    filename = DATA_DIR / 'm1_assignment_repayment.json'
    with open(filename, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # 解析统一格式: {header, rows, rowCount}
    header = json_data['header']
    rows = json_data['rows']

    print(f"  加载 {filename.name}: {len(rows)} 行")
    return rows


def parse_data(data):
    """
    解析数据，按月份和day组织
    注意：SQL返回的数据已经是累积值，无需再累加
    header: [assigned_month, month_day, case_type, assigned_principal, assigned_case_cnt, repaid_principal, repaid_case_cnt]
    如果某一天的repaid_principal为NULL，说明数据未更新完成，跳过该日期
    """
    # 按月份和case_type组织数据（直接使用SQL返回的累积值）
    data_by_month = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
        'assigned_principal': 0,
        'repaid_principal': 0
    })))

    for row in data:
        month, day_full, case_type, assigned_principal, _, repaid_principal, _ = row
        # 从完整日期提取日期数字 (如 "2026-02-01" -> 1)
        day = int(day_full.split('-')[-1])

        # 检查是否为NULL（数据未更新完成）
        if repaid_principal is None or repaid_principal == "NULL":
            # 数据未更新完成，跳过该日期
            continue

        # 处理数据类型（直接使用SQL返回的累积值）
        assigned = float(assigned_principal) if assigned_principal else 0
        repaid = float(repaid_principal) if repaid_principal else 0
        data_by_month[month][day][case_type]['assigned_principal'] = assigned
        data_by_month[month][day][case_type]['repaid_principal'] = repaid

    return data_by_month


def generate_assignment_chart(data_by_month, case_type_filter=None):
    """
    生成分案回款率图表
    case_type_filter: None(整体), "新案", "老案"
    """
    # 横轴：1～31 号位全部出刻度；各月仅在本月历日有效，超出当月天数的号位留空（不画柱/不连线点）
    months = sorted(data_by_month.keys())
    all_days = list(range(1, 32))

    # 准备绘图数据（横轴 1–31 刻度较密，略加宽画布）
    fig, ax1 = plt.subplots(figsize=(14, 6), dpi=100)

    # 月份颜色（随数据月份动态生成）
    colors = chart_theme.month_color_dict(months)

    # 准备分组bar的数据 - 每个月份独立展示，不堆叠
    x_positions = np.arange(len(all_days))
    bar_width = 0.25  # 每个月份bar的宽度
    offsets = {m: (i - len(months)/2 + 0.5) * bar_width for i, m in enumerate(months)}

    # 为每个月份准备数据（分组形式，不堆叠）
    for i, month in enumerate(months):
        assigned_principals = []

        dim = _days_in_month(month)
        for day in all_days:
            if day > dim:
                assigned_principals.append(float('nan'))
            elif day in data_by_month[month]:
                total_assigned = 0
                for case_type in data_by_month[month][day]:
                    if case_type_filter is None or case_type == case_type_filter:
                        total_assigned += data_by_month[month][day][case_type]['assigned_principal']

                assigned_principals.append(total_assigned / 1e6)
            else:
                assigned_principals.append(0)

        # 绘制分组bar（每个月份独立，并列显示）
        bars = ax1.bar(x_positions + offsets[month], assigned_principals,
                      width=bar_width,
                      color=colors[month],
                      alpha=0.82,
                      label=f'{month[5:7]}月')

    # 设置左轴（分案金额）
    ax1.set_xlabel('日期（号）', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.set_ylabel('分案金额（百万）', fontsize=12, fontweight='bold', fontproperties=font_prop)
    # 横轴固定展示每月 1～31 日（全部刻度）
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels(all_days, fontproperties=font_prop, fontsize=8)
    ax1.set_xlim(x_positions[0] - 0.5, x_positions[-1] + 0.5)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:,.0f}'))
    ax1.tick_params(axis='y', labelsize=10)

    # 绘制右轴（回款率折线）
    ax2 = ax1.twinx()

    for i, month in enumerate(months):
        repayment_rates = []
        valid_days = []

        dim = _days_in_month(month)
        for day in all_days:
            if day > dim:
                repayment_rates.append(None)
            elif day in data_by_month[month]:
                total_assigned = 0
                total_repaid = 0

                for case_type in data_by_month[month][day]:
                    if case_type_filter is None or case_type == case_type_filter:
                        total_assigned += data_by_month[month][day][case_type]['assigned_principal']
                        total_repaid += data_by_month[month][day][case_type]['repaid_principal']

                if total_assigned > 0:
                    rate = (total_repaid / total_assigned) * 100
                    repayment_rates.append(rate)
                    valid_days.append(day - 1)  # day-1是索引
                else:
                    repayment_rates.append(None)
            else:
                repayment_rates.append(None)

        # 只绘制有效的点（过滤None）
        valid_indices = [j for j, r in enumerate(repayment_rates) if r is not None]
        if valid_indices:
            valid_x = [x_positions[j] + offsets[month] for j in valid_indices]  # 对齐到对应月份的bar中心
            valid_rates = [repayment_rates[j] for j in valid_indices]

            # 绘制折线
            ax2.plot(valid_x, valid_rates,
                    color=colors[month],
                    linewidth=2,
                    marker='o',
                    markersize=4,
                    alpha=0.9)

            # 只标注最后一个点（每月最后一天）
            if valid_x and valid_rates:
                last_x = valid_x[-1]
                last_rate = valid_rates[-1]
                ax2.annotate(f'{last_rate:.2f}%',
                           xy=(last_x, last_rate),
                           xytext=(0, 6),
                           textcoords='offset points',
                           fontsize=9,
                           color=chart_theme.ANNOTATE_COLOR,
                           ha='center',
                           fontproperties=font_prop)

    # 设置右轴（回款率）
    ax2.set_ylabel('回款率 (%)', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax2.tick_params(axis='y', labelsize=10)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}%'))

    # 设置y轴范围，给顶部留空间
    all_rates = []
    for month in months:
        dim = _days_in_month(month)
        for day in all_days:
            if day > dim:
                continue
            if day in data_by_month[month]:
                total_assigned = 0
                total_repaid = 0
                for case_type in data_by_month[month][day]:
                    if case_type_filter is None or case_type == case_type_filter:
                        total_assigned += data_by_month[month][day][case_type]['assigned_principal']
                        total_repaid += data_by_month[month][day][case_type]['repaid_principal']
                if total_assigned > 0:
                    all_rates.append((total_repaid / total_assigned) * 100)

    if all_rates:
        max_rate = max(all_rates)
        ax2.set_ylim(bottom=0, top=max_rate * 1.15)
    else:
        ax2.set_ylim(bottom=0)

    chart_theme.style_axes_light(ax1, grid_axis='y')

    chart_theme.polish_twin_bars_and_lines(ax1, ax2, stacked_bars=False)

    # 图例
    ax1.legend(loc='upper left', fontsize=10, prop=font_prop)

    # 标题
    if case_type_filter is None:
        title = '分案回款率（整体）'
        filename = 'assignment_repayment_overall.png'
    elif case_type_filter == "新案":
        title = '分案回款率（新案）'
        filename = 'assignment_repayment_new.png'
    else:
        title = '分案回款率（老案）'
        filename = 'assignment_repayment_old.png'

    plt.title(title, fontsize=28, fontweight='bold', fontproperties=font_prop, pad=20, color=chart_theme.TEXT_PRIMARY)
    plt.tight_layout()

    output_path = OUTPUT_DIR / filename
    chart_theme.save_figure(fig, output_path, dpi=150)
    plt.close()

    print(f'  OK: {filename}')


def _m1_cum_repayment_rate_for_day(data_by_month, month: str, day: int, case_type_filter):
    """
    返回该 assigned_month、日历日的累积回款率（%）；与柱线图同一套口径（SQL 已为累积值）。
    case_type_filter: None（新案+老案） / "新案" / "老案"
    """
    dim = _days_in_month(month)
    if day > dim or day not in data_by_month[month]:
        return None
    total_a = 0.0
    total_r = 0.0
    for ct, v in data_by_month[month][day].items():
        if case_type_filter is not None and ct != case_type_filter:
            continue
        total_a += float(v.get("assigned_principal") or 0)
        total_r += float(v.get("repaid_principal") or 0)
    if total_a <= 0:
        return None
    return (total_r / total_a) * 100.0


def generate_m1_table_charts(data_by_month):
    """
    三张纯表图：最近 3 个 assigned_month × 日 1–31 的累积回款率（%），风格对齐 recovery_rate_S_table_*.png
    """
    all_months = sorted(data_by_month.keys())
    months = all_months[-3:]
    while len(months) < 3:
        months = [""] + months
    months = months[-3:]
    month_labels = {m: chart_theme.month_label_cn(m) if m else "" for m in months}

    specs = [
        (None, "assignment_repayment_table_overall.png", "M1 分案累积回款率对比表（整体）"),
        ("新案", "assignment_repayment_table_new.png", "M1 分案累积回款率对比表（新案）"),
        ("老案", "assignment_repayment_table_old.png", "M1 分案累积回款率对比表（老案）"),
    ]

    ncol = 4  # Day + 3 months

    for case_type_filter, out_name, title in specs:
        table_data = []
        heat_rows: list[list[float | None]] = []
        for day in range(1, 32):
            row = [str(day)]
            row_heat: list[float | None] = [None]
            for m in months:
                if not m:
                    row.append("-")
                    row_heat.append(None)
                    continue
                rate = _m1_cum_repayment_rate_for_day(data_by_month, m, day, case_type_filter)
                row.append(f"{rate:.2f}%" if rate is not None else "-")
                row_heat.append(rate)
            table_data.append(row)
            heat_rows.append(row_heat)

        nums = [x for r in heat_rows for x in r if x is not None]
        if nums:
            vmin, vmax = min(nums), max(nums)
            if vmax - vmin < 1e-3:
                vmin -= 0.5
                vmax += 0.5
        else:
            vmin, vmax = 0.0, 1.0

        fig, ax = plt.subplots(figsize=(10.5, 11))
        chart_theme.prepare_screen_table_figure(fig, ax)

        header_row = ["Day"] + [month_labels[m] for m in months]
        full_table_data = [header_row] + table_data

        tbl = ax.table(
            cellText=full_table_data,
            cellLoc="center",
            loc="center",
            bbox=chart_theme.TABLE_AX_BBOX,
        )
        tbl.auto_set_font_size(False)
        fm = font_manager.FontProperties(family="DengXian")

        chart_theme.style_screen_table_simple_header(tbl, ncol=ncol, row_index=0, font_prop=fm, fontsize=11)
        chart_theme.style_screen_table_body(
            tbl,
            data_row_start=1,
            nrows=len(full_table_data),
            ncol=ncol,
            font_prop=fm,
            day_col=0,
            percent_cols=frozenset(range(1, ncol)),
            data_fontsize=9,
            heatmap_values=heat_rows,
            heatmap_vmin=vmin,
            heatmap_vmax=vmax,
        )

        chart_theme.set_screen_table_title(ax, title)

        out_path = OUTPUT_DIR / out_name
        chart_theme.save_figure(
            fig,
            out_path,
            dpi=150,
            save_facecolor=chart_theme.AXES_PANEL if chart_theme.VISUAL_STYLE == "dashboard" else chart_theme.FIG_FACE,
        )
        plt.close()
        print(f"  OK: {out_name}")


def cleanup_old_charts(pattern):
    """清理旧图表文件"""
    old_files = list(OUTPUT_DIR.glob(pattern))
    if old_files:
        for f in old_files:
            f.unlink()
        print(f"[清除旧图表] {len(old_files)} 张\n")


def main():
    """主函数：生成所有M1分案回款图表"""
    print("=" * 60)
    print("开始生成M1分案回款率图表...")
    print(f"数据目录: {DATA_DIR}")
    print(f"保存位置: {OUTPUT_DIR}")
    print("=" * 60)

    # 清除旧的 M1 图表（含柱线图与纯表图）
    cleanup_old_charts("assignment_repayment_*.png")

    # 加载并解析数据
    data = load_data()
    data_by_month = parse_data(data)

    # 柱线图 3 张 + 纯表图 3 张
    print("\n生成图表:")
    generate_assignment_chart(data_by_month, case_type_filter=None)
    generate_assignment_chart(data_by_month, case_type_filter="新案")
    generate_assignment_chart(data_by_month, case_type_filter="老案")
    print("\n生成对比表:")
    generate_m1_table_charts(data_by_month)

    print("\n" + "=" * 60)
    print("M1 分案回款图表生成完成！共 6 张（3 柱线 + 3 表）")
    print("=" * 60)


if __name__ == '__main__':
    main()
