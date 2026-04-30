"""
生成GRP催收员图表
数据源: ../../data/grp_collector.json（与 run_all 落盘文件名一致）
输出: 12张图表 (各case_type的collector_ins分组对比图)
"""
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager
import pandas as pd
import numpy as np
import json
from pathlib import Path

# 设置中文字体和样式
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DengXian']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['axes.facecolor'] = '#FFFFFF'
matplotlib.rcParams['figure.facecolor'] = '#FFFFFF'
font_prop = font_manager.FontProperties(family='DengXian')

# 数据和输出目录
DATA_DIR = Path(__file__).parent.parent.parent / 'data'
OUTPUT_DIR = Path(__file__).parent.parent.parent / 'screenshots'
OUTPUT_DIR.mkdir(exist_ok=True)


def load_grp_data():
    """加载GRP数据"""
    filename = DATA_DIR / 'grp_collector.json'
    with open(filename, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # 解析统一格式: {header, rows, rowCount}
    header = json_data['header']
    rows = json_data['rows']

    print(f"  加载 {filename.name}: {len(rows)} 行")

    # 转换为DataFrame
    df = pd.DataFrame(rows, columns=header)

    # 数据类型转换
    df['dt'] = df['dt'].astype(int)
    df['repaid_principal'] = df['repaid_principal'].astype(float)
    df['mtd_daily_assign_amt'] = df['mtd_daily_assign_amt'].astype(float)

    return df


def process_grp_data(df):
    """处理数据，计算累积值"""
    if df is None or df.empty:
        return {}

    print("\n处理数据...")

    # 按月份、case_type、dt排序
    df = df.sort_values(['mth', 'case_type', 'dt', 'collector_ins'])

    # 找到最新月份的最大天数（用于同期对比）
    latest_month = df['mth'].max()
    max_day_in_latest = df[df['mth'] == latest_month]['dt'].max()
    print(f"  最新月份: {latest_month}, 数据截至: {max_day_in_latest}号")

    # 按月份和case_type分组
    result = {}

    for (mth, case_type), group in df.groupby(['mth', 'case_type']):
        # 同期对比：只保留<=max_day_in_latest的数据
        group = group[group['dt'] <= max_day_in_latest].copy()

        if group.empty:
            continue

        # 获取所有collector_ins
        collectors = sorted(group['collector_ins'].unique())

        # 获取所有天数
        days = sorted(group['dt'].unique())

        # 初始化数据矩阵
        cumsum_assign = pd.DataFrame(index=days, columns=collectors, dtype=float).fillna(0)
        cumsum_repaid = pd.DataFrame(index=days, columns=collectors, dtype=float).fillna(0)

        # 填充数据
        for _, row in group.iterrows():
            dt = row['dt']
            collector = row['collector_ins']
            cumsum_assign.loc[dt, collector] += row['mtd_daily_assign_amt']
            cumsum_repaid.loc[dt, collector] += row['repaid_principal']

        # 计算每个collector的累积值
        for collector in collectors:
            cumsum_assign[collector] = cumsum_assign[collector].cumsum()
            cumsum_repaid[collector] = cumsum_repaid[collector].cumsum()

        # 计算累积回款率：cumsum_assign 早期可能为 0 导致 inf，需要先把 inf 换成 NaN 再 fillna(0)
        # 否则 inf 会污染后续 max_rate 计算 → 右轴范围被错误压缩
        cumsum_rate = (cumsum_repaid / cumsum_assign * 100).replace([np.inf, -np.inf], np.nan).fillna(0)

        key = (mth, case_type)
        result[key] = {
            'cumsum_repaid': cumsum_repaid,
            'cumsum_assign': cumsum_assign,
            'cumsum_rate': cumsum_rate,
            'collectors': collectors,
            'max_day': max_day_in_latest
        }

    print(f"  处理完成，共 {len(result)} 个数据组")
    return result


def plot_grp_chart(data_dict, case_type, output_path):
    """
    绘制单个case_type的对比图（一个坐标轴展示两个月）

    参数:
        data_dict: 处理后的数据字典 {(mth, case_type): {...}}
        case_type: 要绘制的case_type
        output_path: 输出路径
    """
    # 筛选该case_type的数据
    case_data = {k: v for k, v in data_dict.items() if k[1] == case_type}

    if not case_data:
        print(f"  跳过: {case_type} 没有数据")
        return False

    # 按月份排序
    months = sorted(set(k[0] for k in case_data.keys()))

    if len(months) < 2:
        # 如果只有一个月，复制一份
        if len(months) == 1:
            months = [months[0], months[0]]

    last_month = months[0]
    current_month = months[-1]

    # 获取数据
    last_data = case_data.get((last_month, case_type))
    curr_data = case_data.get((current_month, case_type))

    if not last_data or not curr_data:
        print(f"  跳过: {case_type} 缺少必要的数据")
        return False

    # 创建单个图表
    fig, ax = plt.subplots(1, 1, figsize=(18, 6))

    # 设置白色背景
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    # 定义配色方案（更现代化的配色）
    colors = ['#FF7043', '#42A5F5', '#66BB6A', '#FFA726', '#AB47BC', '#26C6DA', '#FFCA28',
              '#EC407A', '#5C6BC0', '#9CCC65', '#FF5252', '#7E57C2', '#26A69A', '#FFA726']

    # 绘制合并图表
    ranking_text = plot_combined_months(ax, last_data, curr_data, last_month, current_month, colors)

    # 设置总标题（美化：更大字号，添加背景色）
    title = f"分职场业绩_{case_type}"
    fig.suptitle(title, fontsize=18, fontweight='bold', y=0.98,
                color='#333333', fontproperties=font_prop)

    # 在底部添加排序文字（美化：添加背景和边框）
    if ranking_text:
        # 固定字体大小
        text_fontsize = 13

        # 添加背景框
        fig.text(0.08, 0.02, ranking_text, ha='left', fontsize=text_fontsize,
                fontweight='bold', color='#333333', fontproperties=font_prop,
                bbox=dict(boxstyle='round,pad=0.6', facecolor='#F5F5F5',
                         edgecolor='#DDDDDD', linewidth=1, alpha=0.8))

    # 固定布局：底部5%给图例，顶部4%边距，图表占91%
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])

    # 保存 - 移除bbox_inches='tight'避免自动裁剪导致布局错乱
    plt.savefig(output_path, dpi=150, facecolor='white', edgecolor='none')
    plt.close()

    print(f"  OK: {output_path.name}")
    return True


def plot_combined_months(ax, last_data, curr_data, last_month, current_month, colors):
    """
    在一个坐标轴里绘制两个月的数据

    本函数设计为支持任意数量的collectors（催收员/区域）：
    - 自动处理两个月collectors数量不一致的情况（填充缺失为0）
    - 动态调整颜色、字体大小、标签间隔
    - 支持1-20+个collectors，无需修改代码
    """
    if last_data is None or curr_data is None:
        return ""

    # 获取数据
    last_assign = last_data['cumsum_assign'].copy()
    last_rate = last_data['cumsum_rate'].copy()
    curr_assign = curr_data['cumsum_assign'].copy()
    curr_rate = curr_data['cumsum_rate'].copy()

    # 修正：显示数据用两个月的并集（3月有PM就显示，4月没有就不显示）
    # 但排序文字只统计最新月份的collectors
    all_collectors = sorted(set(last_data['collectors']) | set(curr_data['collectors']))
    curr_collectors_only = sorted(curr_data['collectors'])  # 用于底部排序文字

    # 确保两个月的DataFrame都包含所有collectors（填充缺失的为0）
    for collector in all_collectors:
        if collector not in last_assign.columns:
            last_assign[collector] = 0
            last_rate[collector] = 0
        if collector not in curr_assign.columns:
            curr_assign[collector] = 0
            curr_rate[collector] = 0

    # 使用all_collectors绘制（显示所有月份出现过的）
    collectors = all_collectors

    # 获取天数
    last_days = last_assign.index.tolist()
    curr_days = curr_assign.index.tolist()

    # 计算X轴位置
    n_last = len(last_days)
    n_curr = len(curr_days)
    gap = 1  # 两个月之间的间隔

    x_last = np.arange(n_last)
    x_curr = np.arange(n_curr) + n_last + gap

    # === 绘制堆叠柱状图（美化：增加边框，调整透明度）===
    # 上个月（数据单位元 → 显示单位百万元）
    bottom_last = np.zeros(n_last)
    for i, collector in enumerate(collectors):
        if collector in last_assign.columns:
            values = last_assign[collector].values / 1e6
            color = colors[i % len(colors)]
            ax.bar(x_last, values, bottom=bottom_last, color=color, alpha=0.85,
                  label=collector, width=0.65, edgecolor='white', linewidth=0.5)
            bottom_last += values

    # 本月（数据单位元 → 显示单位百万元）
    bottom_curr = np.zeros(n_curr)
    for i, collector in enumerate(collectors):
        if collector in curr_assign.columns:
            values = curr_assign[collector].values / 1e6
            color = colors[i % len(colors)]
            ax.bar(x_curr, values, bottom=bottom_curr, color=color, alpha=0.85,
                  width=0.65, edgecolor='white', linewidth=0.5)
            bottom_curr += values

    # === 创建第二个Y轴用于回款率 ===
    ax2 = ax.twinx()

    # 存储每个collector在本月最后一天的回款率（用于排序）
    final_rates = {}

    # 绘制折线图（美化：增加阴影效果，优化线条）
    for i, collector in enumerate(collectors):
        color = colors[i % len(colors)]

        # 上个月折线
        if collector in last_rate.columns:
            rate_last = last_rate[collector].values
            ax2.plot(x_last, rate_last, color=color, linewidth=3.0,
                    marker='o', markersize=5, markeredgewidth=1.5, markeredgecolor='white',
                    alpha=0.9, zorder=3)

        # 本月折线
        if collector in curr_rate.columns:
            rate_curr = curr_rate[collector].values
            ax2.plot(x_curr, rate_curr, color=color, linewidth=3.0,
                    marker='o', markersize=5, markeredgewidth=1.5, markeredgecolor='white',
                    alpha=0.9, zorder=3)

            # 记录本月最后一天的回款率（用于排序）
            curr_val = rate_curr[-1]
            final_rates[collector] = curr_val

    # === 设置X轴（美化：更清晰的标签）===
    all_x = np.concatenate([x_last, x_curr])
    all_labels = [str(d) for d in last_days] + [str(d) for d in curr_days]
    ax.set_xticks(all_x)
    ax.set_xticklabels(all_labels, fontsize=10, fontproperties=font_prop, color='#666666')

    # 在X轴上方添加月份标识（美化：更大字号，加粗）
    last_month_label = f"{last_month[:4]}-{last_month[4:]}"
    current_month_label = f"{current_month[:4]}-{current_month[4:]}"

    ax.text(x_last[len(x_last)//2], ax.get_ylim()[1] * 1.08,
           last_month_label,
           ha='center', va='bottom', fontsize=14, fontweight='bold',
           fontproperties=font_prop, color='#333333')
    ax.text(x_curr[len(x_curr)//2], ax.get_ylim()[1] * 1.08,
           current_month_label,
           ha='center', va='bottom', fontsize=14, fontweight='bold',
           fontproperties=font_prop, color='#333333')

    # === 设置Y轴 ===
    # 左Y轴（金额）：统一为"百万"单位（百万元 IDR）
    # 数据已 / 1e6；关闭 matplotlib 自动 offset，避免出现 1e6/1e7 的量级标记
    ax.set_ylabel('累积分案金额 (百万)', fontsize=11, fontweight='bold', labelpad=10)
    max_amount = max(bottom_last.max(), bottom_curr.max())
    if max_amount <= 0 or np.isnan(max_amount):
        max_amount = 1
    ax.set_ylim(0, max_amount * 1.15)
    ax.ticklabel_format(axis='y', style='plain', useOffset=False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:,.0f}'))

    # 右Y轴（回款率）：起始固定 0%，上限按【本图】实际数据 *1.2 动态调整
    # 每张图根据自己 case_type 的两月折线最大值独立设置范围，互相不影响
    ax2.set_ylabel('累积回款率 (%)', fontsize=11, fontweight='bold', labelpad=10)
    all_rates = pd.concat([last_rate, curr_rate], axis=1).replace([np.inf, -np.inf], np.nan)
    max_rate = all_rates.max().max()
    if pd.isna(max_rate) or max_rate <= 0:
        max_rate = 5
    # 上限 = max(实际最大值 * 1.2, 5%)，保证全 0 数据时图也不被压扁
    ax2.set_ylim(0, max(max_rate * 1.2, 5))

    # === 图例（美化：添加边框和阴影）===
    handles, labels = ax.get_legend_handles_labels()
    legend_ncol = min(len(collectors), 5)
    legend = ax.legend(handles, labels, loc='lower left', fontsize=10,
                      bbox_to_anchor=(0, -0.08), ncol=legend_ncol,
                      frameon=True, fancybox=True, shadow=True,
                      edgecolor='#CCCCCC', prop=font_prop)
    legend.get_frame().set_alpha(0.95)

    # === 网格（美化：更细更淡的网格线）===
    ax.grid(axis='y', alpha=0.15, linestyle='--', linewidth=0.6, color='#CCCCCC')
    ax.set_axisbelow(True)

    # 添加纵向分隔线标识两个月
    ax.axvline(x=n_last + gap/2, color='#DDDDDD', linewidth=1.5, linestyle='--', alpha=0.5, zorder=0)

    # === 生成排序文字（带百分比） ===
    # 只统计最新月份实际存在的collectors
    # final_rates包含所有collectors，需要过滤出当前月存在的
    current_month_rates = {k: v for k, v in final_rates.items() if k in curr_collectors_only}
    sorted_collectors = sorted(current_month_rates.items(), key=lambda x: x[1], reverse=True)

    # 动态调整排序文字：如果collectors太多（>8个），只显示前5名和后1名
    if len(sorted_collectors) > 8:
        top_5 = sorted_collectors[:5]
        last_1 = sorted_collectors[-1:]
        ranking_parts = [f"{c[0]}（{c[1]:.2f}%）" for c in top_5]
        ranking_parts.append("...")
        ranking_parts.extend([f"{c[0]}（{c[1]:.2f}%）" for c in last_1])
        ranking_text = " > ".join(ranking_parts)
    else:
        ranking_text = " > ".join([f"{c[0]}（{c[1]:.2f}%）" for c in sorted_collectors])

    return ranking_text


def cleanup_old_charts(pattern):
    """清理旧图表文件"""
    old_files = list(OUTPUT_DIR.glob(pattern))
    if old_files:
        for f in old_files:
            f.unlink()
        print(f"[清除旧图表] {len(old_files)} 张")


def main():
    """主函数：生成所有GRP图表"""
    print("=" * 60)
    print("开始生成GRP催收员图表...")
    print(f"数据目录: {DATA_DIR}")
    print(f"保存位置: {OUTPUT_DIR}")
    print("=" * 60)

    # 清除旧的GRP图表
    cleanup_old_charts('grp_*.png')

    # 加载数据
    print("\n加载数据:")
    df = load_grp_data()

    if df is None or df.empty:
        print("错误: 无法加载数据")
        return

    # 处理数据
    data_dict = process_grp_data(df)

    if not data_dict:
        print("错误: 数据处理失败")
        return

    # 获取所有case_type
    case_types = sorted(set(k[1] for k in data_dict.keys()))
    print(f"\n找到 {len(case_types)} 个case_type: {case_types}")

    # 为每个case_type生成图表
    print("\n生成图表:")
    success_count = 0

    for case_type in case_types:
        output_path = OUTPUT_DIR / f"grp_{case_type}.png"
        if plot_grp_chart(data_dict, case_type, output_path):
            success_count += 1

    print("\n" + "=" * 60)
    print(f"GRP图表生成完成！成功生成 {success_count}/{len(case_types)} 张图表")
    print("=" * 60)


if __name__ == '__main__':
    main()
