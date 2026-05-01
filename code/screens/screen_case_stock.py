# -*- coding: utf-8 -*-
"""
case_stock 九宫格：3 行（人均库存 / 案件数 / 分案人数）× 3 列（非预测外呼 / 预测外呼 / 整体）。
每行图表下方对齐一张表，填写该列折线各月取值（四舍五入取整、完整数字）。
数据源: ../../data/case_stock.json
输出: screenshots/case_stock_9grid.png
"""
from __future__ import annotations

import json
import sys
import io
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import gridspec

import chart_theme

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

chart_theme.apply_chart_theme()

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = ROOT / "data" / "case_stock.json"
OUT_DIR = ROOT / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

COL_FILTERS = ("非预测外呼", "预测外呼", None)  # None = 整体
COL_TITLES = ("非预测外呼", "预测外呼", "整体")

ROW_KEYS = ("percol", "case_daily", "num_col")
ROW_TITLES = ("人均库存", "案件数", "分案人数")

# 相邻两行「图表行」之间的间距（厘米）
ROW_GAP_CM = 0.5
# 行标题与最左一列坐标轴区域之间的水平间距（厘米）
TITLE_TO_AXES_CM = 0.5


def _fmt_int(v: float) -> str:
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return ""
    return str(int(round(float(v))))


def _mth_label(mth: str) -> str:
    if mth and len(mth) == 6 and mth.isdigit():
        return f"{mth[:4]}-{mth[4:]}"
    return mth


def case_group_sort_key(name: str) -> tuple[int, int, str]:
    """
    堆叠顺序：模块 S1 → S2 → S3；模块内后缀 RA → RB → RC → RD。
    裸写的「S3」（无后缀）排在 S3 模块内最前，再接 S3RA、S3RB 等。
    未知命名排在最后，按字符串兜底。
    """
    g = (name or "").strip()
    if not g:
        return (99, 99, "")
    mod_rank = 99
    tail = g
    if g.startswith("S1"):
        mod_rank, tail = 1, g[2:]
    elif g.startswith("S2"):
        mod_rank, tail = 2, g[2:]
    elif g.startswith("S3"):
        mod_rank, tail = 3, g[2:]
    else:
        return (99, 99, g)

    sub_order = {"RA": 1, "RB": 2, "RC": 3, "RD": 4}
    if tail == "":
        sub_rank = 0
    elif tail in sub_order:
        sub_rank = sub_order[tail]
    else:
        sub_rank = 40
    return (mod_rank, sub_rank, tail or "\0")


def load_rows() -> tuple[list[str], list[list]]:
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    header = data["header"]
    rows = data["rows"]
    need = {"mth", "case_group_type", "col_type", "case_stock_cnt", "num_dt",
            "avg_case_stock_cnt_daily", "avg_num_col_daily", "avg_case_stock_cnt_daily_percol"}
    if not need <= set(header):
        raise ValueError(f"case_stock.json 缺少字段: {need - set(header)}")
    return header, rows


def rows_to_records(header: list[str], rows: list[list]) -> list[dict]:
    idx = {h: i for i, h in enumerate(header)}
    out = []
    for r in rows:
        out.append({
            "mth": r[idx["mth"]],
            "case_group_type": r[idx["case_group_type"]],
            "col_type": r[idx["col_type"]],
            "case_stock_cnt": float(r[idx["case_stock_cnt"]]),
            "num_dt": float(r[idx["num_dt"]]),
            "avg_case_stock_cnt_daily": float(r[idx["avg_case_stock_cnt_daily"]]),
            "avg_num_col_daily": float(r[idx["avg_num_col_daily"]]),
            "avg_case_stock_cnt_daily_percol": float(r[idx["avg_case_stock_cnt_daily_percol"]]),
        })
    return out


def subset(recs: list[dict], col_filter: str | None, mth: str) -> list[dict]:
    if col_filter is None:
        return [x for x in recs if x["mth"] == mth and x["col_type"] in COL_FILTERS[:2]]
    return [x for x in recs if x["mth"] == mth and x["col_type"] == col_filter]


def line_metrics(rows_m: list[dict]) -> tuple[float, float, float]:
    """不拆分 case_group_type / col_type：返回 (人均库存, 案件数日均值, 分案人数合计)。

    人均库存 = sum(case_stock_cnt) / mean(num_dt) / sum(avg_num_col_daily)
    （与 sum(case_stock_cnt)/avg(num_dt)/sum(avg_num_col_daily) 等价写法）
    """
    if not rows_m:
        return float("nan"), float("nan"), float("nan")
    sum_cs = sum(x["case_stock_cnt"] for x in rows_m)
    mean_nd = float(np.mean([x["num_dt"] for x in rows_m]))
    sum_avg_col = sum(x["avg_num_col_daily"] for x in rows_m)
    case_daily = sum_cs / mean_nd if mean_nd else float("nan")
    percol = case_daily / sum_avg_col if sum_avg_col else float("nan")
    return percol, case_daily, sum_avg_col


def metric_for_row(rec: dict, row_key: str) -> float:
    if row_key == "percol":
        return rec["avg_case_stock_cnt_daily_percol"]
    if row_key == "case_daily":
        return rec["avg_case_stock_cnt_daily"]
    return rec["avg_num_col_daily"]


def compute_line_y(
    months: list[str], recs: list[dict], col_filter: str | None, row_key: str
) -> np.ndarray:
    line_y = []
    for mth in months:
        rows_m = subset(recs, col_filter, mth)
        p, c, n = line_metrics(rows_m)
        if row_key == "percol":
            line_y.append(p)
        elif row_key == "case_daily":
            line_y.append(c)
        else:
            line_y.append(n)
    return np.array(line_y, dtype=float)


def plot_cell(
    ax,
    months: list[str],
    recs: list[dict],
    col_filter: str | None,
    row_key: str,
    stack: bool,
    colors: dict[str, tuple[int, str]],
    *,
    draw_line: bool,
    line_alpha: float,
    percol_stack_from_lines: tuple[np.ndarray, np.ndarray] | None = None,
) -> np.ndarray:
    x = np.arange(len(months))
    line_y = compute_line_y(months, recs, col_filter, row_key)

    width = 0.55
    if stack and col_filter is not None:
        group_order = sorted(
            {x["case_group_type"] for x in recs if x["col_type"] == col_filter},
            key=case_group_sort_key,
        )
        bottom = np.zeros(len(months))
        for g in group_order:
            seg = []
            for mth in months:
                row_g = next(
                    (
                        x
                        for x in recs
                        if x["mth"] == mth
                        and x["col_type"] == col_filter
                        and x["case_group_type"] == g
                    ),
                    None,
                )
                seg.append(metric_for_row(row_g, row_key) if row_g else 0.0)
            seg = np.array(seg, dtype=float)
            if seg.sum() <= 0:
                continue
            color = colors[g][1]
            ax.bar(x, seg, width, bottom=bottom, color=color, edgecolor="white", linewidth=0.4)
            for xi, v, btm in zip(x, seg, bottom):
                if v <= 0:
                    continue
                cy = float(btm + v / 2)
                ax.text(
                    xi,
                    cy,
                    f"{g},{_fmt_int(float(v))}",
                    ha="center",
                    va="center",
                    fontsize=6,
                    color="#0F172A",
                    clip_on=False,
                )
            bottom += seg
    else:
        # 整体列 · 人均库存：堆叠仍用第1、2列「折线」人均库存；折线与下表用 line_y（整体不拆 col_type）
        if row_key == "percol" and percol_stack_from_lines is not None:
            s_np = np.asarray(percol_stack_from_lines[0], dtype=float)
            s_pr = np.asarray(percol_stack_from_lines[1], dtype=float)
            type_order = ("非预测外呼", "预测外呼")
            type_colors = ("#93C5FD", "#FB923C")
            bottom = np.zeros(len(months))
            for ti, (ct, seg) in enumerate(zip(type_order, (s_np, s_pr))):
                seg_c = np.nan_to_num(seg, nan=0.0, posinf=0.0, neginf=0.0)
                if seg_c.sum() <= 0:
                    continue
                ax.bar(
                    x,
                    seg_c,
                    width,
                    bottom=bottom,
                    color=type_colors[ti],
                    edgecolor="white",
                    linewidth=0.4,
                    alpha=0.92,
                )
                for xi, v, btm in zip(x, seg_c, bottom):
                    if v <= 0:
                        continue
                    cy = float(btm + v / 2)
                    ax.text(
                        xi,
                        cy,
                        f"{ct},{_fmt_int(float(v))}",
                        ha="center",
                        va="center",
                        fontsize=6,
                        color="#0F172A",
                        clip_on=False,
                    )
                bottom = bottom + seg_c
        # 整体列：案件数 / 分案人数 按 col_type 拆成两叠（各类型下对指标直接 sum）
        elif row_key in ("case_daily", "num_col"):
            type_order = ("非预测外呼", "预测外呼")
            type_colors = ("#93C5FD", "#FB923C")
            bottom = np.zeros(len(months))
            for ti, ct in enumerate(type_order):
                seg = []
                for mth in months:
                    rows_ct = [
                        r for r in recs if r["mth"] == mth and r["col_type"] == ct
                    ]
                    seg.append(sum(metric_for_row(x, row_key) for x in rows_ct))
                seg = np.array(seg, dtype=float)
                if seg.sum() <= 0:
                    continue
                ax.bar(
                    x,
                    seg,
                    width,
                    bottom=bottom,
                    color=type_colors[ti],
                    edgecolor="white",
                    linewidth=0.4,
                    alpha=0.92,
                )
                for xi, v, btm in zip(x, seg, bottom):
                    if v <= 0:
                        continue
                    cy = float(btm + v / 2)
                    ax.text(
                        xi,
                        cy,
                        f"{ct},{_fmt_int(float(v))}",
                        ha="center",
                        va="center",
                        fontsize=6,
                        color="#0F172A",
                        clip_on=False,
                    )
                bottom += seg
        else:
            # 整体列 · 人均库存（无堆叠入参）：单柱 = 折线 = 下表
            totals = np.nan_to_num(np.asarray(line_y, dtype=float), nan=0.0)
            if totals.sum() > 0:
                bars = ax.bar(
                    x,
                    totals,
                    width,
                    color="#94A3B8",
                    edgecolor="white",
                    linewidth=0.5,
                    alpha=0.9,
                )
                for xi, v, rect in zip(x, totals, bars):
                    if v <= 0:
                        continue
                    ax.text(
                        rect.get_x() + rect.get_width() / 2.0,
                        v,
                        _fmt_int(float(v)),
                        ha="center",
                        va="bottom",
                        fontsize=7,
                        color="#0F172A",
                        clip_on=False,
                    )

    if draw_line:
        ax.plot(
            x,
            line_y,
            color="#B91C1C",
            linewidth=2.0,
            marker="o",
            markersize=5,
            zorder=10,
            alpha=line_alpha,
        )
    ax.set_xticks(x)
    # 月份仅在下方表格展示，图上不显示横轴刻度与标签
    ax.tick_params(axis="x", bottom=False, labelbottom=False)

    # 左轴无刻度；仅保留纵向参考时可开横轴网格
    ax.tick_params(axis="y", left=False, labelleft=False)
    ax.yaxis.set_ticks_position("none")
    ax.grid(False)
    ax.grid(True, axis="x", linestyle="--", alpha=0.65)

    return line_y


def add_line_value_table(ax_table, months: list[str], line_y: np.ndarray) -> None:
    ax_table.axis("off")
    ax_table.margins(0)
    row_cells = [[_fmt_int(float(line_y[i])) for i in range(len(months))]]
    col_labels = [_mth_label(m) for m in months]
    # 表格贴紧子图顶部（与上图 hspace=0 时无缝衔接）
    tbl = ax_table.table(
        cellText=row_cells,
        colLabels=col_labels,
        cellLoc="center",
        edges="closed",
        bbox=[0.0, 0.0, 1.0, 1.0],
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7)
    # 纵向 scale 减小 = 行高变矮，表更「扁」
    tbl.scale(1.0, 1.05)
    for (row, col), cell in tbl.get_celld().items():
        cell.set_edgecolor("#CBD5E1")
        cell.set_linewidth(0.65)
        if row == 0:
            cell.set_facecolor("#F1F5F9")
            cell.set_text_props(weight="bold", fontsize=7)
        else:
            cell.set_facecolor("#FFFFFF")


def main() -> int:
    header, rows = load_rows()
    recs = rows_to_records(header, rows)
    months = sorted({x["mth"] for x in recs}, reverse=True)

    all_groups = sorted({x["case_group_type"] for x in recs}, key=case_group_sort_key)
    cmap = chart_theme.SERIES_COLORS
    colors = {g: (i, cmap[i % len(cmap)]) for i, g in enumerate(all_groups)}

    fig_w = 19.0
    fig_h = 15.0
    fig = plt.figure(figsize=(fig_w, fig_h))

    # 三块垂直区域；块与块之间约 ROW_GAP_CM
    inner_h = (fig_h - 1.2) / 3  # 近似单块图表区高度（英寸）
    outer_hspace = (ROW_GAP_CM / 2.54) / inner_h if inner_h > 0 else 0.12

    outer = gridspec.GridSpec(
        3,
        1,
        figure=fig,
        height_ratios=[1, 1, 1],
        hspace=outer_hspace,
        left=0.155,
        right=0.985,
        top=0.91,
        bottom=0.06,
    )

    axes_chart: list[list] = [[], [], []]
    axes_table: list[list] = [[], [], []]

    for ri in range(3):
        inner = outer[ri].subgridspec(
            2,
            3,
            # 表区占垂直比例略小，避免挤压上图（柱内标注等）
            height_ratios=[1, 0.13],
            hspace=0.0,
            wspace=0.0,
        )
        row_axes = []
        for ci in range(3):
            if ci == 0:
                ax_c = fig.add_subplot(inner[0, ci])
            elif ci == 1:
                # 与第 1 列共用 Y 轴量程；整体列单独量程
                ax_c = fig.add_subplot(
                    inner[0, ci],
                    sharex=row_axes[0],
                    sharey=row_axes[0],
                )
            else:
                ax_c = fig.add_subplot(inner[0, ci], sharex=row_axes[0])
            row_axes.append(ax_c)
            ax_t = fig.add_subplot(inner[1, ci])
            axes_chart[ri].append(ax_c)
            axes_table[ri].append(ax_t)

    for ci, cf in enumerate(COL_FILTERS):
        axes_chart[0][ci].set_title(COL_TITLES[ci], fontsize=15, fontweight="bold", pad=12)

    # 先算各格「折线」序列。第一行第三列：堆叠用 col0/col1 人均库存折线，折线/下表用 col2（整体不拆 col_type）
    line_grid: list[list[np.ndarray]] = []
    for ri, rk in enumerate(ROW_KEYS):
        line_grid.append(
            [compute_line_y(months, recs, COL_FILTERS[ci], rk) for ci in range(3)]
        )

    for ri, rk in enumerate(ROW_KEYS):
        draw_line = ri == 0
        line_alpha = 0.5 if draw_line else 1.0
        for ci, cf in enumerate(COL_FILTERS):
            stack = cf is not None
            stack_lines = (
                (line_grid[0][0], line_grid[0][1]) if (ri == 0 and ci == 2) else None
            )
            plot_cell(
                axes_chart[ri][ci],
                months,
                recs,
                cf,
                rk,
                stack,
                colors,
                draw_line=draw_line,
                line_alpha=line_alpha,
                percol_stack_from_lines=stack_lines,
            )
            if ri == 0 and ci == 2:
                tbl_y = line_grid[0][2]
            else:
                tbl_y = line_grid[ri][ci]
            add_line_value_table(axes_table[ri][ci], months, tbl_y)

    gap_f = (TITLE_TO_AXES_CM / 2.54) / fig_w
    text_half_f = (18 / 72) / fig_w

    for ri, title in enumerate(ROW_TITLES):
        pos = axes_chart[ri][0].get_position()
        cx = pos.x0 - gap_f - text_half_f
        cy = pos.y0 + pos.height / 2
        fig.text(
            cx,
            cy,
            title,
            fontsize=16,
            fontweight="bold",
            ha="center",
            va="center",
            rotation=90,
            transform=fig.transFigure,
        )

    out = OUT_DIR / "case_stock_9grid.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print(f"已保存: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
