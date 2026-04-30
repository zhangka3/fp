#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Average Effective Working Time Visualization
根据avg_eff_worktim.json生成人均有效工作时长图表（按模块-队列分组）
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib import font_manager

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DengXian']
plt.rcParams['axes.unicode_minus'] = False

def load_data(json_path):
    """加载JSON数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    def safe_float(val):
        """安全转换为float，处理NULL字符串"""
        if val is None or val == 'NULL' or val == '':
            return None
        return float(val)

    rows = []
    for row in data['rows']:
        # 只保留S1, S2, S3（过滤M2和NULL）
        if row[0] in ['S1', 'S2', 'S3']:
            # 新格式包含area_ranking_type字段
            if len(row) >= 7:  # 新格式
                rows.append({
                    'area_type': row[0],
                    'area_ranking_type': row[1],
                    'p_month': row[2],
                    'scope_x': row[3],
                    'avg_eff_worktime': safe_float(row[4]),
                    'last_avg_eff_worktime': safe_float(row[5]),
                    'diff_avg_eff_worktime': safe_float(row[6])
                })
            else:  # 兼容旧格式
                rows.append({
                    'area_type': row[0],
                    'area_ranking_type': row[0],  # 使用area_type作为默认值
                    'p_month': row[1],
                    'scope_x': row[2],
                    'avg_eff_worktime': safe_float(row[3]),
                    'last_avg_eff_worktime': safe_float(row[4]),
                    'diff_avg_eff_worktime': safe_float(row[5])
                })

    return rows

def prepare_plot_data(rows):
    """准备绘图数据（按模块-队列分组）"""
    # 按area_type+area_ranking_type组合分组
    # 生成组合key，例如"S1-RA", "S2-RC"等
    for row in rows:
        area = row['area_type']
        ranking = row['area_ranking_type']
        # 简化ranking显示：S1RA -> RA, S2RC -> RC
        if ranking and ranking.startswith(area):
            ranking_short = ranking[len(area):]
        else:
            ranking_short = ranking if ranking else area
        row['group_key'] = f"{area}-{ranking_short}"

    # 获取所有group_keys并排序
    group_keys = sorted(list(set(r['group_key'] for r in rows)))

    # 获取所有scope_x并排序
    all_scopes = []
    for group in group_keys:
        group_rows = [r for r in rows if r['group_key'] == group]
        scopes = sorted(list(set(r['scope_x'] for r in group_rows)))
        all_scopes.extend(scopes)

    # 去重并按WK和WD排序
    unique_scopes = []
    seen = set()
    for scope in all_scopes:
        if scope not in seen:
            unique_scopes.append(scope)
            seen.add(scope)

    # 按WK和WD排序
    def scope_sort_key(s):
        parts = s.split('-')
        wk = int(parts[0].replace('WK', ''))
        wd = int(parts[1].replace('WD', ''))
        return (wk, wd)

    unique_scopes.sort(key=scope_sort_key)

    # 构建数据字典
    plot_data = {}
    for group in group_keys:
        plot_data[group] = {
            'scopes': [],
            'months': {},
            'diffs': []
        }

        group_rows = [r for r in rows if r['group_key'] == group]
        months = sorted(list(set(r['p_month'] for r in group_rows)))

        # 找到该group有数据的scope
        group_scopes = [s for s in unique_scopes if any(r['scope_x'] == s for r in group_rows)]
        plot_data[group]['scopes'] = group_scopes

        # 按月份组织数据
        for month in months:
            month_rows = [r for r in group_rows if r['p_month'] == month]
            month_data = {}
            for row in month_rows:
                month_data[row['scope_x']] = row['avg_eff_worktime']
            plot_data[group]['months'][month] = month_data

        # 获取diff数据（只有最新月份）
        if months:
            latest_month = max(months)
            diff_data = {}
            for row in group_rows:
                if row['p_month'] == latest_month:
                    diff_data[row['scope_x']] = row['diff_avg_eff_worktime']
            plot_data[group]['diffs'] = diff_data

    return plot_data, group_keys

def plot_avg_eff_worktime(data_path, output_path, chart_title='人均日均有效工作时长（整体）'):
    """绘制人均有效工作时长图表

    chart_title: 图表主标题，按数据源不同传不同的副名（整体 / Call / WA）
    """

    # 加载数据
    rows = load_data(data_path)
    plot_data, group_keys = prepare_plot_data(rows)

    # 创建图表
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(24, 10),
                                     gridspec_kw={'height_ratios': [2, 1], 'hspace': 0.05})

    # 月份颜色映射
    month_colors = {
        '2026-02': '#E8A5C9',  # 浅粉
        '2026-03': '#9B7EBF',  # 中紫
        '2026-04': '#5D3A91'   # 深紫
    }

    # 准备X轴位置
    x_positions = {}
    current_x = 0
    for group in group_keys:
        scopes = plot_data[group]['scopes']
        for i, scope in enumerate(scopes):
            x_positions[f"{group}_{scope}"] = current_x + i
        current_x += len(scopes) + 2  # 每个group之间留2个单位间隔

    # ===== 上半部分：折线图 =====
    # 用于跟踪已添加的图例
    legend_added = set()

    for group in group_keys:
        scopes = plot_data[group]['scopes']
        months_data = plot_data[group]['months']

        x_coords = [x_positions[f"{group}_{s}"] for s in scopes]

        for month, color in month_colors.items():
            if month in months_data:
                y_values = [months_data[month].get(s, None) for s in scopes]

                # 不过滤None值，让matplotlib自动在None处断开线条
                if any(y is not None for y in y_values):
                    # 只为每个月份添加一次图例
                    label = month if month not in legend_added else None
                    if label:
                        legend_added.add(month)

                    ax1.plot(x_coords, y_values, color=color, linewidth=2.5,
                            marker='o', markersize=4, label=label, alpha=0.8)

    # 添加group背景色和标签
    y_max = max([max([v for v in month_data.values() if v is not None], default=0)
                 for group_data in plot_data.values()
                 for month_data in group_data['months'].values()], default=500)

    for i, group in enumerate(group_keys):
        scopes = plot_data[group]['scopes']
        if scopes:
            x_start = x_positions[f"{group}_{scopes[0]}"] - 0.5
            x_end = x_positions[f"{group}_{scopes[-1]}"] + 0.5

            # 交替使用浅灰和白色背景
            bgcolor = '#F5F5F5' if i % 2 == 0 else 'white'
            ax1.axvspan(x_start, x_end, facecolor=bgcolor, alpha=0.5, zorder=0)
            ax2.axvspan(x_start, x_end, facecolor=bgcolor, alpha=0.5, zorder=0)

            # 添加group标签在顶部
            x_mid = (x_start + x_end) / 2
            ax1.text(x_mid, y_max * 1.05, group,
                    ha='center', va='bottom', fontsize=12, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray',
                             edgecolor='darkgray', alpha=0.8))

    # ===== 下半部分：柱状图 =====
    for group in group_keys:
        scopes = plot_data[group]['scopes']
        diffs = plot_data[group]['diffs']

        x_coords = [x_positions[f"{group}_{s}"] for s in scopes]
        y_values = [diffs.get(s, 0) if diffs.get(s) is not None else 0 for s in scopes]

        # 根据正负值设置颜色
        colors = ['#5FD0C8' if v >= 0 else '#FF6B6B' for v in y_values]

        bars = ax2.bar(x_coords, y_values, width=0.8, color=colors, alpha=0.8)

        # 在柱子上方添加数值标签（只标注非零值）
        for x, y, bar in zip(x_coords, y_values, bars):
            if abs(y) > 0.1:  # 只标注绝对值大于0.1的
                label_y = y + (5 if y >= 0 else -5)
                ax2.text(x, label_y, f'{int(y)}',
                        ha='center', va='bottom' if y >= 0 else 'top',
                        fontsize=7, fontweight='bold')

    # ===== 设置X轴标签 =====
    all_x_ticks = []
    all_x_labels = []

    for group in group_keys:
        scopes = plot_data[group]['scopes']

        # 按WK分组添加分隔线
        current_wk = None
        for i, scope in enumerate(scopes):
            x_pos = x_positions[f"{group}_{scope}"]
            wk = scope.split('-')[0]

            # 如果WK变化，添加分隔线
            if current_wk is not None and wk != current_wk:
                ax1.axvline(x=x_pos - 0.5, color='gray', linestyle=':', alpha=0.5, linewidth=1)
                ax2.axvline(x=x_pos - 0.5, color='gray', linestyle=':', alpha=0.5, linewidth=1)

            current_wk = wk

            # 使用原始scope_x作为标签
            all_x_ticks.append(x_pos)
            all_x_labels.append(scope)

    ax1.set_xticks([])
    ax2.set_xticks(all_x_ticks)
    ax2.set_xticklabels(all_x_labels, rotation=90, fontsize=6, ha='center')

    # ===== 设置X轴范围（去掉左右留白） =====
    if all_x_ticks:
        x_min = min(all_x_ticks)
        x_max = max(all_x_ticks)
        ax1.set_xlim([x_min - 0.5, x_max + 0.5])
        ax2.set_xlim([x_min - 0.5, x_max + 0.5])

    # ===== 设置Y轴 =====
    # 计算Y轴范围
    y_max = max([max([v for v in month_data.values() if v is not None], default=0)
                 for group_data in plot_data.values()
                 for month_data in group_data['months'].values()], default=500)
    y_min = min([min([v for v in month_data.values() if v is not None], default=0)
                 for group_data in plot_data.values()
                 for month_data in group_data['months'].values()], default=200)

    ax1.set_ylim([y_min * 0.9, y_max * 1.15])  # 留出空间给group标签

    ax1.set_ylabel('人均有效工作时长 (分钟)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('环比差值 (分钟)', fontsize=12, fontweight='bold')

    ax1.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax2.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax2.axhline(y=0, color='black', linewidth=1, alpha=0.5)

    # ===== 设置图例（上移到 ax1 顶部外侧，横向排列，不挡数据）=====
    ax1.legend(
        loc='lower right',
        bbox_to_anchor=(1.0, 1.02),
        fontsize=11,
        framealpha=0.9,
        ncol=len(month_colors),
        frameon=True,
    )

    # ===== 设置标题（按数据源动态命名）=====
    fig.suptitle(f'{chart_title}趋势及环比变化（按模块-队列分组）',
                 fontsize=16, fontweight='bold', y=0.98)

    # ===== 调整布局 =====
    plt.tight_layout()

    # ===== 保存图表 =====
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"图表已保存到: {output_path}")
    plt.close()

if __name__ == '__main__':
    # 项目根：本文件位于 code/screens/
    _ROOT = Path(__file__).resolve().parent.parent.parent
    BASE_DATA = _ROOT / 'data'
    BASE_OUT = _ROOT / 'screenshots'
    BASE_OUT.mkdir(parents=True, exist_ok=True)

    targets = [
        ('avg_eff_worktim.json',      'avg_eff_worktime.png',      '人均日均有效工作时长（整体）'),
        ('avg_eff_call_worktim.json', 'avg_eff_call_worktime.png', '人均日均有效工作时长（Call）'),
        ('avg_eff_wa_worktim.json',   'avg_eff_wa_worktime.png',   '人均日均有效工作时长（WA）'),
    ]
    for src, dst, title in targets:
        src_path = BASE_DATA / src
        dst_path = BASE_OUT / dst
        if not src_path.exists():
            print(f"[SKIP] {src} 不存在")
            continue
        plot_avg_eff_worktime(str(src_path), str(dst_path), chart_title=title)
