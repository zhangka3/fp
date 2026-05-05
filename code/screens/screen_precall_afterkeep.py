#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
留案与留案后外呼（pre_call_after_reverse）：**行 = 指标**，**列 = 手工/全时 × stage**。

数据：`data/precall_afterkeep.json`（`17_precall_afterkeep.sql` → `run_all.py`）。
输出：`screenshots/precall_afterkeep_trends.png`

版式对齐 **`precall_task_trends.png`**（`screen_precall_task.py`）：
- **3 行**（自上而下）：留案率 `keep_rate`、留案后案均拨次 `avg_callcnt_percase_afterkeep`、留案后接通率 `conn_rate_afterkeep`。
- **列**：手工各 stage + **1 cm 空白** + 全时各 stage；列间 wspace=0；**stage 列序与 `precall_task_trends.png` 一致**：RA→RB→RC→RD→S2→S3→M2→M4→M5；细粒度 **`S[123]RA|RB|RC|RD`** 归入对应粗槽，同槽 **S1<S2<S3**，其后为未识别 stage 按名排序。
- 分隔线、折线仅连有数据日期（不插值）、列顶 type/stage 标题：同 precall_task。
"""

from __future__ import annotations

import json
import re
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
DATA_PATH = ROOT / "data" / "precall_afterkeep.json"
OUT_PATH = ROOT / "screenshots" / "precall_afterkeep_trends.png"

BASE_FIG_W_IN = 10.0
DPI = 150
NUM_CALENDAR_DAYS = 60

COL_PRE_TYPES = ("手工", "全时")

# (metric_key, y轴标签, 点旁标注格式：pct=百分比 num=两位小数)
ROW_METRICS = (
    ("keep_rate", "留案率", "pct"),
    ("avg_callcnt_percase_afterkeep", "留案后案均拨次", "num"),
    ("conn_rate_afterkeep", "留案后接通率", "pct"),
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

STAGE_DIVIDER_LW = 2.0
PRE_TYPE_DIVIDER_LW = 5.0
DIVIDER_COLOR = chart_theme.TEXT_PRIMARY

LEFT_MARGIN = 0.07
RIGHT_MARGIN = 0.015
GAP_CM = 1.0
TOP_MAIN = 0.88
BOTTOM_MAIN = 0.07
Y_STAGE_HDR = TOP_MAIN + 0.018
Y_TYPE_HEAD = TOP_MAIN + 0.052

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

# 与 precall_task 数据源粗粒度 stage 对齐；本表多为 S1RA、S2RB 等
_FINE_STAGE_RE = re.compile(r"^S([123])(RA|RB|RC|RD)$", re.IGNORECASE)


def _stage_sort_key(st: str) -> tuple:
    """列顺序对齐 `screen_precall_task` / `precall_task_trends.png`：先按 RA…M5 槽位，再粗粒度先于 S* 细粒度，同槽 S1<S2<S3。"""
    st_raw = str(st).strip()
    st_norm = st_raw.upper()
    if st_norm in _STAGE_ORDER_RANK:
        return (_STAGE_ORDER_RANK[st_norm], 0, 0, st_raw)
    m = _FINE_STAGE_RE.match(st_norm)
    if m:
        band = int(m.group(1))
        suf = m.group(2).upper()
        coarse_idx = {"RA": 0, "RB": 1, "RC": 2, "RD": 3}[suf]
        return (coarse_idx, 1, band, st_raw)
    return (len(STAGE_DISPLAY_ORDER) + 1, 9, 99, st_raw)


def _named_indices(header: list[str]) -> dict:
    """支持两种表头：① `mm_dd` + `pre_type`；② `dt`（yyyyMMdd）+ `type`（与 Hive 落盘一致）。"""
    idx = {h: i for i, h in enumerate(header)}
    for k in ("stage", "keep_rate", "avg_callcnt_percase_afterkeep", "conn_rate_afterkeep"):
        if k not in idx:
            raise ValueError(f"precall_afterkeep header 缺少字段: {k}")
    if "pre_type" in idx:
        i_pre = idx["pre_type"]
    elif "type" in idx:
        i_pre = idx["type"]
    else:
        raise ValueError("precall_afterkeep header 需含 pre_type 或 type")
    if "mm_dd" in idx:
        date_kind = "mm_dd"
        i_date = idx["mm_dd"]
    elif "dt" in idx:
        date_kind = "dt_yyyymmdd"
        i_date = idx["dt"]
    else:
        raise ValueError("precall_afterkeep header 需含 mm_dd 或 dt")
    return {
        "date_kind": date_kind,
        "i_date": i_date,
        "pre_type": i_pre,
        "stage": idx["stage"],
        "keep_rate": idx["keep_rate"],
        "avg_callcnt_percase_afterkeep": idx["avg_callcnt_percase_afterkeep"],
        "conn_rate_afterkeep": idx["conn_rate_afterkeep"],
    }


def _row_to_date(row: list, ix: dict, anchor: date) -> date:
    if ix["date_kind"] == "mm_dd":
        return _mmdd_to_date(row[ix["i_date"]], anchor)
    s = str(row[ix["i_date"]]).strip().replace("-", "")
    if len(s) < 8:
        raise ValueError(f"dt 非 yyyyMMdd: {row[ix['i_date']]!r}")
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


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


def _fmt_ann(val: float | None, fmt: str) -> str:
    if val is None or np.isnan(val):
        return ""
    if fmt == "pct":
        return f"{val:.1%}"
    return f"{val:.2f}"


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

    metric_keys = tuple(m[0] for m in ROW_METRICS)
    cube: dict[tuple[str, str], dict[date, dict[str, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )

    for row in rows:
        pt = row[ix["pre_type"]]
        st = row[ix["stage"]]
        try:
            dt = _row_to_date(row, ix, anchor)
        except (ValueError, TypeError):
            continue
        if dt < window_start or dt > window_end:
            continue
        for mk in metric_keys:
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

    n_metrics = len(ROW_METRICS)
    fig_w_in = max(16.0, min(44.0, BASE_FIG_W_IN + 2.35 * n_col))
    gap_f = (GAP_CM / 2.54) / fig_w_in
    fig_h_in = max(11.0, min(22.0, 6.8 + 1.55 * n_metrics))

    inner_left = LEFT_MARGIN
    inner_right = 1.0 - RIGHT_MARGIN
    have_gap = n_lm > 0 and n_rm > 0
    span_w = inner_right - inner_left - (gap_f if have_gap else 0.0)
    col_w = span_w / max(n_col, 1)
    row_h = (TOP_MAIN - BOTTOM_MAIN) / float(n_metrics)

    def col_left(k: int) -> float:
        if k < n_lm:
            return inner_left + k * col_w
        return inner_left + n_lm * col_w + (gap_f if have_gap else 0.0) + (k - n_lm) * col_w

    fig = plt.figure(figsize=(fig_w_in, fig_h_in), dpi=DPI)
    palette = chart_theme.MONTH_LINE_COLORS

    for r, (metric_key, metric_label, ann_fmt) in enumerate(ROW_METRICS):
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
                    yvi = yvals[xi]
                    if np.isnan(yvi):
                        continue
                    ax.annotate(
                        _fmt_ann(float(yvi), ann_fmt),
                        xy=(x_num[xi], yvi),
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

    for k in range(1, n_col):
        thick_boundary = have_gap and k == n_lm
        _vdivider(col_left(k), PRE_TYPE_DIVIDER_LW if thick_boundary else STAGE_DIVIDER_LW)
    if have_gap and n_lm > 0:
        _vdivider(inner_left + n_lm * col_w, PRE_TYPE_DIVIDER_LW)

    fig.suptitle(
        f"留案与留案后外呼（近 {NUM_CALENDAR_DAYS} 日，截至 {anchor_s}）",
        fontsize=SUPTITLE_FS,
        fontweight="bold",
        y=0.98,
        color=chart_theme.TEXT_PRIMARY,
    )

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
