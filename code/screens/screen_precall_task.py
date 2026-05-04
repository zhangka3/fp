#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预测试任务（pre_call）：**行 = 指标**，**列 = type（手工/全时）× stage**。

数据：`data/precall_task.json`（`16_precall_task.sql` → `run_all.py`）。
输出：`screenshots/precall_task_trends.png`

版式：
- **4 行**：接通率、呼损率、有效时间利用率、人工接通语音信箱比例（自上而下）。
- **列**：先 **手工** 下各 stage，再 **与「全时」之间固定 1 cm 空白**，再 **全时** 各 stage；列间 **wspace=0**，行间 **hspace=0**（无缝拼接）。
- **stage 列顺序**（每个 type 内仅排数据中出现的项）：**RA → RB → RC → RD → S2 → S3 → M2 → M4 → M5**；未在表内的 stage 排在最后并按名称排序。
- **相邻 stage 列**之间 **细** 竖线；**手工** 与 **全时** 两组之间（含空隙两侧边界）**更粗** 竖线。
- 每格一条折线（该 type、该 stage、该行指标）；横轴 **由远到近**；无刻度；无图例。
- **时间**：**不向序列插入任何日期**，不做插值。某日若无观测则图上 **既不画点也不占位**；
  仅按数据中 **实际出现的日期** 顺序连线（例如仅 3/7、3/9 有值则 **3/7 直连 3/9**，3/8 不当作存在）。
"""

from __future__ import annotations

import json
import sys
import io
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import numpy as np

import chart_theme

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

chart_theme.apply_chart_theme()

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = ROOT / "data" / "precall_task.json"
OUT_PATH = ROOT / "screenshots" / "precall_task_trends.png"

BASE_FIG_W_IN = 10.0
DPI = 150
NUM_CALENDAR_DAYS = 60

COL_PRE_TYPES = ("手工", "全时")

ROW_METRICS = (
    ("conn_ratio", "接通率"),
    ("conn_loss_ratio", "呼损率"),
    ("eff_duration_ratio", "有效时间利用率"),
    ("vm_ratio_agent_conn", "人工接通中的语音信箱比例"),
)

ANNOT_FS = 9
SUPTITLE_FS = 16
COL_HEAD_FS = 22
STAGE_HDR_FS = 11
METRIC_YLABEL_FS = 12

LINEWIDTH = 1.55
MARKERSIZE = 4.0
MARKER_EDGE_W = 0.85
POLISH_STROKE_EXTRA = 1.65

# 竖向分隔线（figure 坐标）
STAGE_DIVIDER_LW = 2.0
PRE_TYPE_DIVIDER_LW = 5.0
DIVIDER_COLOR = chart_theme.TEXT_PRIMARY

LEFT_MARGIN = 0.07
RIGHT_MARGIN = 0.015
# 「手工」列组与「全时」列组之间的空白宽度（厘米，按导出画布宽度换算进 figure）
GAP_CM = 1.0
TOP_MAIN = 0.88
BOTTOM_MAIN = 0.07
Y_STAGE_HDR = TOP_MAIN + 0.018
Y_TYPE_HEAD = TOP_MAIN + 0.052


# 业务约定列顺序（每个 type 内：仅展示数据中存在的 stage）
STAGE_DISPLAY_ORDER: tuple[str, ...] = (
    "RA",
    "RB",
    "RC",
    "RD",
    "S2",
    "S3",
    "M2",
    "M4",
    "M5",
)

_STAGE_ORDER_RANK: dict[str, int] = {name: i for i, name in enumerate(STAGE_DISPLAY_ORDER)}


def _stage_sort_key(st: str) -> tuple:
    st_norm = str(st).strip().upper()
    if st_norm in _STAGE_ORDER_RANK:
        return (0, _STAGE_ORDER_RANK[st_norm])
    return (1, st_norm)


def _named_indices(header: list[str]) -> dict[str, int]:
    named = {
        "pre_type",
        "stage",
        "conn_loss_ratio",
        "conn_ratio",
        "eff_duration_ratio",
        "vm_ratio_agent_conn",
    }
    idx = {h: i for i, h in enumerate(header)}
    extras = [i for i, h in enumerate(header) if h not in named]
    if len(extras) != 1:
        raise ValueError(f"precall_task header 需恰有一列日期(MM-dd)，实际额外列: {extras}")
    return {
        "mmdd": extras[0],
        "pre_type": idx["pre_type"],
        "stage": idx["stage"],
        "conn_loss_ratio": idx["conn_loss_ratio"],
        "conn_ratio": idx["conn_ratio"],
        "eff_duration_ratio": idx["eff_duration_ratio"],
        "vm_ratio_agent_conn": idx["vm_ratio_agent_conn"],
    }


def _mmdd_to_date(mmdd: str, anchor: date) -> date:
    mo, dy = map(int, str(mmdd).strip().split("-"))
    y = anchor.year
    dt = date(y, mo, dy)
    if dt > anchor:
        dt = date(y - 1, mo, dy)
    return dt


def _safe_float(v) -> float | None:
    if v is None or v == "" or v == "NULL":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fmt_metric(val: float | None) -> str:
    if val is None or np.isnan(val):
        return ""
    return f"{val:.1%}"


def _annotation_days(dates_ord: list[date], yvals: np.ndarray) -> set[int]:
    valid = np.flatnonzero(~np.isnan(yvals))
    if valid.size == 0:
        return set()
    idx_latest = int(valid[-1])
    want: set[int] = {idx_latest}

    latest_d = dates_ord[idx_latest]
    start_d = dates_ord[0]
    step = latest_d
    while True:
        step = step - timedelta(days=7)
        if step < start_d:
            break
        try:
            want.add(dates_ord.index(step))
        except ValueError:
            pass

    yi = yvals[valid]
    vi = valid
    imax = int(vi[int(np.nanargmax(yi))])
    imin = int(vi[int(np.nanargmin(yi))])
    want.add(imax)
    want.add(imin)
    return want


def _facet_hide_spines(ax: plt.Axes, *, top: bool, bottom: bool, left: bool, right: bool) -> None:
    ax.spines["top"].set_visible(top)
    ax.spines["bottom"].set_visible(bottom)
    ax.spines["left"].set_visible(left)
    ax.spines["right"].set_visible(right)


def _compact_xy(x_num_arr: np.ndarray, yvals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """仅保留「源数据里真正有值」的日历点，按时间升序，用于 plot。

    - **不**补点、**不**插值、**不**为缺日虚构时间；缺日在图中不出现。
    - 相邻两个有值日之间用线段连接（时间轴上跨过中间缺口），中间日期 **不代表** 有观测。
    """
    mask = ~np.isnan(yvals)
    return x_num_arr[mask], yvals[mask]


def main() -> int:
    if not DATA_PATH.is_file():
        print(f"✗ 找不到数据: {DATA_PATH}")
        return 1

    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    meta = raw.get("metadata") or {}
    anchor_s = meta.get("data_fetch_date")
    if not anchor_s:
        print("✗ metadata 缺少 data_fetch_date")
        return 1
    anchor = datetime.strptime(str(anchor_s), "%Y-%m-%d").date()

    header = raw["header"]
    rows = raw["rows"]
    ix = _named_indices(header)

    window_end = anchor
    window_start = anchor - timedelta(days=NUM_CALENDAR_DAYS - 1)
    day_list = [window_start + timedelta(days=i) for i in range(NUM_CALENDAR_DAYS)]
    day_to_x = {d: i for i, d in enumerate(day_list)}
    x_num = mdates.date2num(day_list)

    cube: dict[tuple[str, str], dict[date, dict[str, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )

    for row in rows:
        pt = row[ix["pre_type"]]
        st = row[ix["stage"]]
        dt = _mmdd_to_date(row[ix["mmdd"]], anchor)
        if dt < window_start or dt > window_end:
            continue
        for mk in ("conn_ratio", "conn_loss_ratio", "eff_duration_ratio", "vm_ratio_agent_conn"):
            v = _safe_float(row[ix[mk]])
            if v is not None:
                cube[(pt, st)][dt][mk] = v

    stages_by_type: list[list[str]] = []
    for pre_type in COL_PRE_TYPES:
        stages_by_type.append(
            sorted({st for (pt, st) in cube if pt == pre_type}, key=_stage_sort_key)
        )

    n_lm = len(stages_by_type[0])
    n_rm = len(stages_by_type[1])
    n_col = n_lm + n_rm
    if n_col == 0:
        print("✗ 无 stage 数据")
        return 1

    column_specs: list[tuple[str, str]] = [
        (COL_PRE_TYPES[0], st) for st in stages_by_type[0]
    ] + [(COL_PRE_TYPES[1], st) for st in stages_by_type[1]]

    fig_w_in = max(16.0, min(44.0, BASE_FIG_W_IN + 2.35 * n_col))
    gap_f = (GAP_CM / 2.54) / fig_w_in
    fig_h_in = max(11.0, min(22.0, 6.8 + 1.55 * 4))

    inner_left = LEFT_MARGIN
    inner_right = 1.0 - RIGHT_MARGIN
    have_gap = n_lm > 0 and n_rm > 0
    span_w = inner_right - inner_left - (gap_f if have_gap else 0.0)
    col_w = span_w / max(n_col, 1)
    row_h = (TOP_MAIN - BOTTOM_MAIN) / 4.0

    def col_left(k: int) -> float:
        if k < n_lm:
            return inner_left + k * col_w
        return inner_left + n_lm * col_w + (gap_f if have_gap else 0.0) + (k - n_lm) * col_w

    fig = plt.figure(figsize=(fig_w_in, fig_h_in), dpi=DPI)
    palette = chart_theme.MONTH_LINE_COLORS

    n_metrics = len(ROW_METRICS)

    for r, (metric_key, metric_label) in enumerate(ROW_METRICS):
        bottom = BOTTOM_MAIN + (n_metrics - 1 - r) * row_h
        for k, (pre_type, st) in enumerate(column_specs):
            color = palette[k % len(palette)]
            left = col_left(k)
            ax = fig.add_axes([left, bottom, col_w, row_h])

            yvals = np.full(NUM_CALENDAR_DAYS, np.nan, dtype=float)
            for dt, mdict in cube[(pre_type, st)].items():
                if metric_key in mdict and dt in day_to_x:
                    yvals[day_to_x[dt]] = mdict[metric_key]

            xv, yv = _compact_xy(x_num, yvals)
            if xv.size:
                ax.plot(
                    xv,
                    yv,
                    color=color,
                    linewidth=LINEWIDTH,
                    marker="o",
                    markersize=MARKERSIZE,
                    markeredgecolor="white",
                    markeredgewidth=MARKER_EDGE_W,
                    alpha=0.92,
                )
                for xi in sorted(_annotation_days(day_list, yvals)):
                    yv = yvals[xi]
                    if np.isnan(yv):
                        continue
                    ax.annotate(
                        _fmt_metric(float(yv)),
                        xy=(x_num[xi], yv),
                        xytext=(0, 6),
                        textcoords="offset points",
                        fontsize=ANNOT_FS,
                        color=color,
                        fontweight="bold",
                        ha="center",
                        va="bottom",
                    )

            chart_theme.polish_ax_lines(ax, stroke_extra=POLISH_STROKE_EXTRA)

            ax.set_yticks([])
            ax.tick_params(axis="y", labelleft=False, length=0)
            ax.tick_params(
                axis="x",
                which="both",
                bottom=False,
                top=False,
                labelbottom=False,
                length=0,
            )
            ax.set_xticklabels([])
            ax.set_xlabel("")
            ax.grid(True, axis="y", alpha=0.85, linestyle="--")
            ax.set_xlim(
                mdates.date2num(day_list[0]) - 0.35,
                mdates.date2num(day_list[-1]) + 0.35,
            )

            if k == 0:
                ax.set_ylabel(
                    metric_label,
                    fontsize=METRIC_YLABEL_FS,
                    fontweight="bold",
                    color=chart_theme.TEXT_PRIMARY,
                )

            first_row = r == 0
            last_row = r == n_metrics - 1
            first_col = k == 0
            last_col = k == len(column_specs) - 1
            _facet_hide_spines(
                ax,
                top=first_row,
                bottom=last_row,
                left=first_col,
                right=last_col,
            )

    def _vdivider(x_fig: float, lw: float) -> None:
        fig.add_artist(
            Line2D(
                [x_fig, x_fig],
                [BOTTOM_MAIN, TOP_MAIN],
                transform=fig.transFigure,
                linewidth=lw,
                color=DIVIDER_COLOR,
                solid_capstyle="butt",
                zorder=100,
                clip_on=False,
            )
        )

    # stage 之间：细线（列左边界 k≥1）；手工|全时：粗线（空隙两侧 + 全时首列左缘）
    for k in range(1, n_col):
        thick_boundary = have_gap and k == n_lm
        _vdivider(col_left(k), PRE_TYPE_DIVIDER_LW if thick_boundary else STAGE_DIVIDER_LW)
    if have_gap and n_lm > 0:
        _vdivider(inner_left + n_lm * col_w, PRE_TYPE_DIVIDER_LW)

    fig.suptitle(
        f"预测试任务指标（近 {NUM_CALENDAR_DAYS} 日，截至 {anchor_s}）",
        fontsize=SUPTITLE_FS,
        fontweight="bold",
        y=0.98,
        color=chart_theme.TEXT_PRIMARY,
    )

    # 列顶：每个 type 一块大字；其下每个 stage 一列小字
    if n_lm > 0:
        cx_m = (col_left(0) + col_left(n_lm - 1) + col_w) / 2.0
        fig.text(
            cx_m,
            Y_TYPE_HEAD,
            COL_PRE_TYPES[0],
            ha="center",
            va="bottom",
            fontsize=COL_HEAD_FS,
            fontweight="bold",
            color=chart_theme.TEXT_PRIMARY,
            transform=fig.transFigure,
        )
        for k in range(n_lm):
            tcx = col_left(k) + col_w / 2.0
            fig.text(
                tcx,
                Y_STAGE_HDR,
                column_specs[k][1],
                ha="center",
                va="bottom",
                fontsize=STAGE_HDR_FS,
                fontweight="bold",
                color=chart_theme.TEXT_PRIMARY,
                transform=fig.transFigure,
            )

    if n_rm > 0:
        k0 = n_lm
        cx_f = (col_left(k0) + col_left(k0 + n_rm - 1) + col_w) / 2.0
        fig.text(
            cx_f,
            Y_TYPE_HEAD,
            COL_PRE_TYPES[1],
            ha="center",
            va="bottom",
            fontsize=COL_HEAD_FS,
            fontweight="bold",
            color=chart_theme.TEXT_PRIMARY,
            transform=fig.transFigure,
        )
        for j in range(n_rm):
            k = k0 + j
            tcx = col_left(k) + col_w / 2.0
            fig.text(
                tcx,
                Y_STAGE_HDR,
                column_specs[k][1],
                ha="center",
                va="bottom",
                fontsize=STAGE_HDR_FS,
                fontweight="bold",
                color=chart_theme.TEXT_PRIMARY,
                transform=fig.transFigure,
            )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    chart_theme.save_figure(fig, OUT_PATH, dpi=DPI)
    plt.close(fig)
    print(f"✓ 已保存 {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
