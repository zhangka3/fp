# -*- coding: utf-8 -*-
"""
M2（单案件类型）与 M2-M6 账龄段（31–180 天）回款率图。
数据源: data/M2_class_all.json, data/M6_class_all.json
风格对齐 S 类：堆叠柱（累积分案基数）+ 双轴折线（累积回款率）+ 对比表图（日 1–31 × 最近三月）。
"""
from __future__ import annotations

import io
import json
import sys

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

import chart_theme

chart_theme.apply_chart_theme()

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "screenshots"
OUTPUT_DIR.mkdir(exist_ok=True)


def _header_idx(header: list) -> dict[str, int]:
    return {name: i for i, name in enumerate(header)}


def _build_chart_data(rows: list, idx: dict[str, int]) -> dict:
    """按月份聚合日维度，计算与 S 类一致的分母 assigned+overdue_added 与累积回款率。"""
    chart_data: dict = defaultdict(
        lambda: {"days": [], "assigned": [], "overdue_added": [], "repaid": [], "rate": []}
    )

    for row in rows:
        p_month = row[idx["p_month"]]
        day_num = int(float(row[idx["day"]]))
        assigned = row[idx["assigned_principal"]]
        overdue_added = row[idx["overdue_added_principal"]]
        repaid = row[idx["repaid_principal"]]
        av = float(assigned) if assigned not in (None, "") else 0.0
        ov = float(overdue_added) if overdue_added not in (None, "") else 0.0
        rv = float(repaid) if repaid not in (None, "") else 0.0
        base = av + ov
        rate = (rv / base * 100) if base > 0 else 0.0
        chart_data[p_month]["days"].append(day_num)
        chart_data[p_month]["assigned"].append(assigned)
        chart_data[p_month]["overdue_added"].append(overdue_added)
        chart_data[p_month]["repaid"].append(repaid)
        chart_data[p_month]["rate"].append(rate)

    for month in chart_data:
        dm = chart_data[month]
        days = dm["days"]
        assigned = dm["assigned"]
        overdue_added = dm["overdue_added"]
        repaid = dm["repaid"]
        order = sorted(range(len(days)), key=lambda i: days[i])
        dm["days"] = [days[i] for i in order]
        dm["assigned"] = [assigned[i] for i in order]
        dm["overdue_added"] = [overdue_added[i] for i in order]
        dm["repaid"] = [repaid[i] for i in order]

        total_a = total_o = total_r = 0.0
        cum_a, cum_o, cum_r = [], [], []
        for i in range(len(dm["days"])):
            total_a += float(dm["assigned"][i] or 0)
            total_o += float(dm["overdue_added"][i] or 0)
            total_r += float(dm["repaid"][i] or 0)
            cum_a.append(total_a)
            cum_o.append(total_o)
            cum_r.append(total_r)
        cum_base = [cum_a[i] + cum_o[i] for i in range(len(cum_a))]
        dm["cum_assigned"] = [x / 1e6 for x in cum_base]
        dm["cum_repaid"] = cum_r
        cum_rate = []
        for i in range(len(cum_base)):
            cum_rate.append((cum_r[i] / cum_base[i] * 100) if cum_base[i] > 0 else 0.0)
        dm["cum_rate"] = cum_rate

    return chart_data


def _plot_combo(chart_data: dict, title: str, png_name: str) -> None:
    fig, ax1 = plt.subplots(figsize=(14, 6))
    months = sorted(chart_data.keys())
    if not months:
        plt.close()
        print(f"  跳过（无月份）: {png_name}")
        return
    colors = chart_theme.month_color_dict(months)
    month_labels = {m: chart_theme.month_label_cn(m) for m in months}
    max_day = max(max(chart_data[m]["days"]) for m in months)
    x_positions = list(range(1, max_day + 1))
    bottom_values = np.zeros(max_day)

    for month in months:
        dm = chart_data[month]
        days = dm["days"]
        cum_assigned = dm["cum_assigned"]
        assigned_by_day = [0] * (max_day + 1)
        for j, day in enumerate(days):
            if day <= max_day:
                assigned_by_day[day] = cum_assigned[j]
        ax1.bar(
            x_positions,
            assigned_by_day[1:],
            bottom=bottom_values,
            color=colors[month],
            alpha=0.85,
        )
        bottom_values += np.array(assigned_by_day[1:])

    ax1.set_xlabel("天数", fontsize=12)
    ax1.set_ylabel("累积分案金额 (百万)", fontsize=12, color="black")
    ax1.tick_params(axis="y", labelcolor="black")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:,.0f}"))
    ax1.set_xlim(0.5, max_day + 0.5)
    ax1.set_xticks(range(1, max_day + 1))
    ax1.tick_params(axis="x", labelsize=8)
    chart_theme.style_axes_light(ax1, grid_axis="y")

    ax2 = ax1.twinx()
    for month in months:
        dm = chart_data[month]
        days = dm["days"]
        cum_rate = dm["cum_rate"]
        ax2.plot(
            days,
            cum_rate,
            marker="o",
            linewidth=2,
            markersize=4,
            label=month_labels[month],
            color=colors[month],
        )
        if days:
            last_day, last_rate = days[-1], cum_rate[-1]
            ax2.plot(
                last_day,
                last_rate,
                "o",
                color=chart_theme.LAST_POINT_MARKER,
                markersize=6,
                zorder=10,
            )
            ax2.annotate(
                f"{last_rate:.2f}%",
                xy=(last_day, last_rate),
                xytext=(6, 6),
                textcoords="offset points",
                fontsize=9,
                fontweight="bold",
                color=chart_theme.ANNOTATE_COLOR,
            )
    ax2.set_ylabel("累积回款率 (%)", fontsize=12, color="black")
    ax2.tick_params(axis="y", labelcolor="black")
    ax2.legend(loc="upper left", prop={"size": 10})
    chart_theme.polish_twin_bars_and_lines(ax1, ax2, stacked_bars=True)
    plt.title(title, fontsize=14, fontweight="bold", pad=15)
    plt.tight_layout()
    out = OUTPUT_DIR / png_name
    chart_theme.save_figure(fig, out, dpi=150)
    plt.close()
    print(f"  OK: {out.name}")


def _plot_table(chart_data: dict, table_title: str, png_name: str) -> None:
    """单行表头：Day + 最近三个月百分比列（与 S 表一致的数据语义，列数=4）。"""
    months_all = sorted(chart_data.keys())
    months = months_all[-3:]
    while len(months) < 3:
        months = [""] + months
    months = months[-3:]
    month_labels = {m: chart_theme.month_label_cn(m) if m else "" for m in months}

    case_month_cum_rate: dict = {}
    for mkey in months:
        if not mkey or mkey not in chart_data:
            continue
        dm = chart_data[mkey]
        days = dm["days"]
        cum_a = cum_o = cum_r = 0.0
        cum_rate_by_day: dict[int, float] = {}
        for i in range(len(days)):
            cum_a += float(dm["assigned"][i] or 0)
            cum_o += float(dm["overdue_added"][i] or 0)
            cum_r += float(dm["repaid"][i] or 0)
            base = cum_a + cum_o
            cum_rate_by_day[days[i]] = (cum_r / base * 100) if base > 0 else 0.0
        case_month_cum_rate[mkey] = cum_rate_by_day

    table_rows = []
    heat_vals: list[list[float | None]] = []
    for day in range(1, 32):
        row = [str(day)]
        hv_row: list[float | None] = [None]
        for mk in months:
            if mk in case_month_cum_rate and day in case_month_cum_rate[mk]:
                v = case_month_cum_rate[mk][day]
                row.append(f"{v:.2f}%")
                hv_row.append(v)
            else:
                row.append("-")
                hv_row.append(None)
        table_rows.append(row)
        heat_vals.append(hv_row)

    ncol = 4
    header = ["Day"] + [month_labels[m] for m in months]
    full_data = [header] + table_rows
    nrows = len(full_data)

    fig, ax = plt.subplots(figsize=(14, 11))
    chart_theme.prepare_screen_table_figure(fig, ax)
    table = ax.table(
        cellText=full_data,
        cellLoc="center",
        loc="center",
        bbox=chart_theme.TABLE_AX_BBOX,
    )
    table.auto_set_font_size(False)
    fp = font_manager.FontProperties(family="DengXian")
    chart_theme.style_screen_table_simple_header(table, ncol=ncol, row_index=0, font_prop=fp, fontsize=11)

    pct = frozenset(range(1, ncol))
    flat_pct = [c for r in heat_vals for c in r[1:] if c is not None]
    vmin = min(flat_pct) if flat_pct else 0.0
    vmax = max(flat_pct) if flat_pct else 100.0
    if vmin >= vmax:
        vmax = vmin + 1e-6

    chart_theme.style_screen_table_body(
        table,
        data_row_start=1,
        nrows=nrows,
        ncol=ncol,
        font_prop=fp,
        day_col=0,
        percent_cols=pct,
        data_fontsize=9,
        heatmap_values=heat_vals,
        heatmap_vmin=vmin,
        heatmap_vmax=vmax,
    )
    chart_theme.set_screen_table_title(ax, table_title)
    out = OUTPUT_DIR / png_name
    chart_theme.save_figure(
        fig,
        out,
        dpi=150,
        save_facecolor=chart_theme.AXES_PANEL if chart_theme.VISUAL_STYLE == "dashboard" else chart_theme.FIG_FACE,
    )
    plt.close()
    print(f"  OK: {out.name}")


def _run_one(json_stem: str, combo_title: str, table_title: str, combo_file: str, table_file: str) -> None:
    path = DATA_DIR / f"{json_stem}.json"
    if not path.exists():
        print(f"  [SKIP] 缺少 {path.name}")
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    header = data["header"]
    rows = data["rows"]
    idx = _header_idx(header)
    for col in ("p_month", "day", "assigned_principal", "overdue_added_principal", "repaid_principal"):
        if col not in idx:
            print(f"  ✗ {json_stem}: 缺少列 {col}")
            return
    chart_data = _build_chart_data(rows, idx)
    print(f"  {json_stem}: {len(rows)} 行, 月份 {sorted(chart_data.keys())}")
    _plot_combo(chart_data, combo_title, combo_file)
    _plot_table(chart_data, table_title, table_file)


def main() -> None:
    print("=" * 60)
    print("M2 / M2-M6 回款率图（S 类风格：组合图 + 表）")
    print(f"数据: {DATA_DIR}")
    print(f"输出: {OUTPUT_DIR}")
    print("=" * 60)

    _run_one(
        "M2_class_all",
        "M2 累积回款率（整体）",
        "M2 累积回款率对比表（整体）",
        "recovery_rate_M2_ALL.png",
        "recovery_rate_M2_table_ALL.png",
    )
    _run_one(
        "M6_class_all",
        "M2-M6（逾期 31–180 天）累积回款率",
        "M2-M6（逾期 31–180 天）累积回款率对比表",
        "recovery_rate_M6_ALL.png",
        "recovery_rate_M6_table_ALL.png",
    )
    print("=" * 60)
    print("完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
