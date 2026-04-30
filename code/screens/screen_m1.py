"""
生成M1分案回款图表
数据源: ../../data/m1_assignment_repayment.json
输出: 3张图表 (整体 + 新案 + 老案)
"""
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager
import numpy as np
import json
from pathlib import Path
from collections import defaultdict

# 设置字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DengXian']
matplotlib.rcParams['axes.unicode_minus'] = False
font_prop = font_manager.FontProperties(family='DengXian')

# 数据和输出目录
DATA_DIR = Path(__file__).parent.parent.parent / 'data'
OUTPUT_DIR = Path(__file__).parent.parent.parent / 'screenshots'
OUTPUT_DIR.mkdir(exist_ok=True)


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
    # 获取所有月份和1-31天
    months = sorted(data_by_month.keys())
    all_days = list(range(1, 32))  # 1-31号

    # 准备绘图数据
    fig, ax1 = plt.subplots(figsize=(12, 6), dpi=100)

    # 月份颜色
    colors = {
        '2026-01': '#FF6B6B',
        '2026-02': '#4ECDC4',
        '2026-03': '#45B7D1',
        '2026-04': '#FFA07A'
    }

    # 准备分组bar的数据 - 每个月份独立展示，不堆叠
    x_positions = np.arange(len(all_days))
    bar_width = 0.25  # 每个月份bar的宽度
    offsets = {m: (i - len(months)/2 + 0.5) * bar_width for i, m in enumerate(months)}

    # 为每个月份准备数据（分组形式，不堆叠）
    for i, month in enumerate(months):
        assigned_principals = []

        for day in all_days:
            if day in data_by_month[month]:
                # 计算该day的数据（合并或筛选case_type）
                total_assigned = 0

                for case_type in data_by_month[month][day]:
                    if case_type_filter is None or case_type == case_type_filter:
                        total_assigned += data_by_month[month][day][case_type]['assigned_principal']

                assigned_principals.append(total_assigned / 1e6)  # 转为百万
            else:
                assigned_principals.append(0)

        # 绘制分组bar（每个月份独立，并列显示）
        bars = ax1.bar(x_positions + offsets[month], assigned_principals,
                      width=bar_width,
                      color=colors[month],
                      alpha=0.6,
                      label=f'{month[5:7]}月')

    # 设置左轴（分案金额）
    ax1.set_xlabel('日期（号）', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.set_ylabel('分案金额（百万）', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax1.set_xticks(x_positions[::2])  # 每隔一天显示刻度
    ax1.set_xticklabels(all_days[::2], fontproperties=font_prop, fontsize=9)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:,.0f}'))
    ax1.tick_params(axis='y', labelsize=10)

    # 绘制右轴（回款率折线）
    ax2 = ax1.twinx()

    for i, month in enumerate(months):
        repayment_rates = []
        valid_days = []

        for day in all_days:
            if day in data_by_month[month]:
                # 数据已经是截止到这一天的累计值
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
                           color='black',
                           ha='center',
                           fontproperties=font_prop)

    # 设置右轴（回款率）
    ax2.set_ylabel('回款率 (%)', fontsize=12, fontweight='bold', fontproperties=font_prop)
    ax2.tick_params(axis='y', labelsize=10)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}%'))

    # 设置y轴范围，给顶部留空间
    all_rates = []
    for month in months:
        for day in all_days:
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

    plt.title(title, fontsize=28, fontweight='bold', fontproperties=font_prop, pad=20)
    plt.tight_layout()

    output_path = OUTPUT_DIR / filename
    plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f'  OK: {filename}')


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

    # 清除旧的M1图表
    cleanup_old_charts('assignment_repayment_*.png')

    # 加载并解析数据
    data = load_data()
    data_by_month = parse_data(data)

    # 生成3张图表
    print("\n生成图表:")
    generate_assignment_chart(data_by_month, case_type_filter=None)
    generate_assignment_chart(data_by_month, case_type_filter="新案")
    generate_assignment_chart(data_by_month, case_type_filter="老案")

    print("\n" + "=" * 60)
    print("M1分案回款率图表生成完成！共 3 张图表")
    print("=" * 60)


if __name__ == '__main__':
    main()
