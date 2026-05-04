#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拨打模式（call_type）周度：上行接通率折线、下行拨打量堆叠柱。

数据：`data/conect_rate.json`（`code/sql/15_conect_rate.sql` → `run_all.py` 落盘）。
输出：`screenshots/call_type_weekly_connect.png`

版式：横轴为自然周，左旧右新；按 `call_type` 分色；画布 **24×16 英寸**、**dpi=150**，
与 `screen_full_call.py` 中 `full_call_eff_rates.png` 一致；上下子图高度比 **4:3**。
大标题与作图区间距 **0.5 cm**；折线点标注在点下方（%），**与同系列折线同色**；同一周内多系列时**垂直错开 + 轻微水平分散**，减轻重叠。
堆叠段内标注拨打量（千分位）。
图例：**左上角**。
横轴仅展示数据中**最近 12 个自然周**（`year`+`week_num` 升序后取末尾 12 个键）。
下图横轴周刻度为大字号；**上图不显示横轴刻度**；上下子图间距约 **0.5 cm**。
**纵轴刻度均不显示**；折线数值标注在点下方约 **0.2 cm**，同周多系列时略加下移/横移防重叠。
"""

from __future__ import annotations

import json
import sys
import io
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np

import chart_theme

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

chart_theme.apply_chart_theme()

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = ROOT / "data" / "conect_rate.json"
OUT_PATH = ROOT / "screenshots" / "call_type_weekly_connect.png"

# 与 full_call 系列一致
FIG_W_IN = 24.0
FIG_H_IN = 16.0
DPI = 150
TITLE_FS = 22
# 与 `screen_full_call` 一致：大标题下沿到作图区上沿约 0.5 cm
TITLE_TO_CHART_GAP_CM = 0.5
# 横轴最多展示最近若干自然周（避免 SQL 窗口过长时图过挤）
NUM_WEEKS = 12
# 折线点下方标注字号（原约 6pt，按「至少 3 倍」放大）
ANNOT_FS = 18
# 柱内拨打量标注：为 Bar 区可读性略小于折线标注（当前为折线的 80%）
ANNOT_FS_BAR = ANNOT_FS * 0.8
# 仅下图横轴周刻度字号（原 8pt 的 2 倍）
WEEK_TICK_FS = 16
# 折线点下方标注：距点约 0.2 cm（offset points）；多系列时再下移/横移防重叠
LINE_LABEL_BELOW_CM = 0.2
LINE_LABEL_BELOW_PT = LINE_LABEL_BELOW_CM / 2.54 * 72.0
LINE_LABEL_STACK_EXTRA_PT = max(11.0, ANNOT_FS * 0.62)
LINE_LABEL_DX_PT = 5.5
# 上下子图间距（厘米，沿 figure 高度换算为 GridSpec hspace）
ROW_GAP_CM = 0.5
# 作图区下边距（略抬高以容纳更大横轴刻度）
GS_BOTTOM = 0.12

# 系列顺序（堆叠自下而上 = 列表从前到后）
CALL_TYPE_ORDER = ("预测外呼", "IVR", "一键多呼", "手拨", "其他")

# 专用色系（与 chart_theme.SERIES_COLORS 马卡龙区分）：色相、明度拉开，便于区分 call_type
_CALL_TYPE_PALETTE = (
    "#1D4ED8",  # blue-700  预测外呼
    "#A21CAF",  # fuchsia-700  IVR
    "#047857",  # emerald-700  一键多呼
    "#C2410C",  # orange-700  手拨
    "#475569",  # slate-600  其他
    "#B91C1C",  # red-700
    "#0E7490",  # cyan-700
    "#A16207",  # yellow-700
    "#5B21B6",  # violet-800
)


def _call_type_colors(n: int) -> list[str]:
    p = list(_CALL_TYPE_PALETTE)
    return [p[i % len(p)] for i in range(n)]


def _safe_float(val) -> float | None:
    if val is None or val == "NULL" or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _safe_int(val) -> int | None:
    if val is None or val == "NULL" or val == "":
        return None
    try:
        return int(str(val).strip())
    except (TypeError, ValueError):
        return None


def _week_label(y: int, w: int) -> str:
    """横轴刻度：两位年 + 周序号，如 2026 年第 1 周 → ``26-W1``。"""
    yy = int(y) % 100
    ww = int(w)
    return f"{yy:02d}-W{ww}"


def _fmt_int_thousands(v: float) -> str:
    return f"{int(round(v)):,}"


def _hspace_for_row_gap_cm(
    fig_h_in: float,
    gs_bottom: float,
    gs_top: float,
    gap_cm: float,
    r0: int = 4,
    r1: int = 3,
) -> float:
    """两子图之间约 ``gap_cm`` 厘米时，对应的 ``GridSpec`` ``hspace``（按 mpl 定义近似）。"""
    gap_frac = gap_cm / 2.54 / fig_h_in
    avail = gs_top - gs_bottom
    if avail <= 0:
        return 0.02
    h0 = avail * r0 / (r0 + r1)
    h1 = avail * r1 / (r0 + r1)
    avg = (h0 + h1) / 2.0
    if avg <= 0:
        return 0.02
    return max(0.004, gap_frac / avg)


def _gridspec_top_for_title(fig, title_fs: float, gap_cm: float) -> tuple[float, float]:
    """suptitle(va=top) 在 y=title_y 时，作图区 GridSpec 可用的 top（figure 归一化）。"""
    fh_in = float(fig.get_figheight())
    gap_frac = (gap_cm / 2.54) / fh_in
    cap_frac = (title_fs * 1.2 / 72.0) / fh_in
    title_y = 0.998
    top_axes = title_y - cap_frac - gap_frac
    return max(0.56, min(top_axes, 0.97)), title_y


def _ordered_call_types(seen: set[str]) -> list[str]:
    out = [c for c in CALL_TYPE_ORDER if c in seen]
    rest = sorted(seen - set(out))
    return out + rest


def load_rows() -> tuple[list[str], list[list]]:
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["header"], data["rows"]


def main() -> int:
    if not DATA_PATH.exists():
        print(f"[SKIP] 缺少 {DATA_PATH}")
        return 0

    header, rows = load_rows()
    idx = {h: i for i, h in enumerate(header)}
    need = ("year", "week_num", "call_type", "connect_rate", "call_cnt")
    for k in need:
        if k not in idx:
            print(f"[ERR] conect_rate.json 缺少列: {k}")
            return 1

    # (year, week) 升序 = 横轴左旧右新
    week_keys: list[tuple[int, int]] = []
    seen_w = set()
    for row in rows:
        y = _safe_int(row[idx["year"]])
        w = _safe_int(row[idx["week_num"]])
        if y is None or w is None:
            continue
        key = (y, w)
        if key not in seen_w:
            seen_w.add(key)
            week_keys.append(key)
    week_keys.sort(key=lambda t: (t[0], t[1]))
    if not week_keys:
        print("[ERR] 无有效周键")
        return 1
    if len(week_keys) > NUM_WEEKS:
        week_keys = week_keys[-NUM_WEEKS:]
    wk_set = set(week_keys)

    def _row_week_key(row: list) -> tuple[int, int] | None:
        y = _safe_int(row[idx["year"]])
        w = _safe_int(row[idx["week_num"]])
        if y is None or w is None:
            return None
        return (y, w)

    call_types = _ordered_call_types(
        {
            str(row[idx["call_type"]]).strip()
            for row in rows
            if row[idx["call_type"]] and _row_week_key(row) in wk_set
        }
    )
    if not call_types:
        print(f"[ERR] 最近 {NUM_WEEKS} 周内无有效 call_type")
        return 1

    wk_index = {wk: i for i, wk in enumerate(week_keys)}
    n = len(week_keys)
    x = np.arange(n, dtype=float)

    # rate[i, j] = week i, call_type j；拨打量矩阵同形
    rate = np.full((n, len(call_types)), np.nan, dtype=float)
    cnt = np.zeros((n, len(call_types)), dtype=float)
    ct_to_j = {c: j for j, c in enumerate(call_types)}

    for row in rows:
        y = _safe_int(row[idx["year"]])
        w = _safe_int(row[idx["week_num"]])
        if y is None or w is None:
            continue
        key = (y, w)
        if key not in wk_index:
            continue
        ct = str(row[idx["call_type"]]).strip()
        if ct not in ct_to_j:
            continue
        j = ct_to_j[ct]
        wi = wk_index[key]
        r = _safe_float(row[idx["connect_rate"]])
        c = _safe_float(row[idx["call_cnt"]])
        if r is not None:
            rate[wi, j] = r * 100.0
        if c is not None:
            cnt[wi, j] = c

    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))
    gs_top, title_y = _gridspec_top_for_title(fig, float(TITLE_FS), TITLE_TO_CHART_GAP_CM)
    hspace = _hspace_for_row_gap_cm(FIG_H_IN, GS_BOTTOM, gs_top, ROW_GAP_CM)
    gs = fig.add_gridspec(
        2,
        1,
        height_ratios=[4, 3],
        hspace=hspace,
        left=0.08,
        right=0.98,
        top=gs_top,
        bottom=GS_BOTTOM,
    )
    ax_top = fig.add_subplot(gs[0, 0])
    ax_bot = fig.add_subplot(gs[1, 0], sharex=ax_top)

    colors = _call_type_colors(len(call_types))
    bar_w = max(0.35, min(0.72, 0.55))

    # 上行：各 call_type 接通率折线（标注在设好 Y 轴后统一画，便于错开与留白）
    for j, ct in enumerate(call_types):
        ys = rate[:, j]
        c = colors[j % len(colors)]
        ax_top.plot(
            x,
            ys,
            color=c,
            linewidth=2.6,
            marker="o",
            markersize=5,
            markeredgecolor="white",
            markeredgewidth=0.9,
            alpha=0.92,
            label=ct,
        )

    ax_top.set_ylabel("接通率 (%)", fontsize=11, fontweight="bold", color=chart_theme.TEXT_PRIMARY)
    ax_top.set_xticks(x)
    ax_top.set_xticklabels([])
    ax_top.tick_params(axis="x", which="both", bottom=False, top=False, labelbottom=False)
    ax_top.grid(True, axis="y", alpha=0.85, linestyle="--")
    ax_top.set_xlim(x.min() - 0.5, x.max() + 0.5)
    nct = len(call_types)
    fin = rate[np.isfinite(rate)]
    if fin.size:
        lo = max(0.0, float(np.nanmin(fin)) * 0.92)
        hi = float(np.nanmax(fin)) * 1.08 + 1e-6
        span = max(hi - lo, 1e-6)
        # 点下放标注 + 多系列时有限错开，预留纵轴下留白
        lo = max(0.0, lo - span * (0.10 + 0.035 * min(max(0, nct - 1), 5)))
        ax_top.set_ylim(lo, hi if hi > lo else lo + 1.0)

    # 同周各点：默认距点向下约 0.2 cm；多系列时按接通率排序并略加下移/横移防重叠
    for xi in range(n):
        pairs = [(j, rate[xi, j]) for j in range(nct) if np.isfinite(rate[xi, j])]
        if not pairs:
            continue
        pairs.sort(key=lambda t: float(t[1]))
        nh = len(pairs)
        for rank, (j, yv) in enumerate(pairs):
            c = colors[j % len(colors)]
            dy = -(
                LINE_LABEL_BELOW_PT
                + (float(rank) * LINE_LABEL_STACK_EXTRA_PT if nh > 1 else 0.0)
            )
            dx = (
                (float(rank) - 0.5 * float(nh - 1)) * LINE_LABEL_DX_PT if nh > 1 else 0.0
            )
            ax_top.annotate(
                f"{float(yv):.2f}%",
                xy=(float(xi), float(yv)),
                xytext=(dx, dy),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=ANNOT_FS,
                color=c,
                clip_on=True,
                zorder=12,
            )

    ax_top.tick_params(axis="y", which="both", left=False, labelleft=False)
    ax_top.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.0),
        borderaxespad=0.6,
        ncol=1,
        fontsize=9,
        frameon=True,
        fancybox=True,
        facecolor=chart_theme.LEGEND_FACE,
        edgecolor=chart_theme.SPINE_COLOR,
    )
    chart_theme.polish_ax_lines(ax_top, stroke_extra=2.0)

    # 下行：堆叠柱（自下而上 = CALL_TYPE_ORDER 顺序）+ 段内千分位标注
    bottom = np.zeros(n, dtype=float)
    week_totals = cnt.sum(axis=1)
    for j, ct in enumerate(call_types):
        h = cnt[:, j]
        c = colors[j % len(colors)]
        rects = ax_bot.bar(
            x,
            h,
            width=bar_w,
            bottom=bottom,
            color=c,
            edgecolor="white",
            linewidth=0.6,
            alpha=0.9,
        )
        patches = getattr(rects, "patches", rects)
        for rect, hh, wtot in zip(patches, h, week_totals):
            if hh <= 0 or wtot <= 0:
                continue
            # 过薄段不写字，避免叠在一起
            if hh < max(wtot * 0.02, 1.0):
                continue
            cx = rect.get_x() + rect.get_width() / 2.0
            cy = rect.get_y() + hh / 2.0
            ax_bot.text(
                cx,
                cy,
                _fmt_int_thousands(hh),
                ha="center",
                va="center",
                fontsize=ANNOT_FS_BAR,
                fontweight="bold",
                color="#FFFFFF",
                path_effects=[
                    pe.withStroke(linewidth=4.0, foreground="#0F172A", alpha=0.45),
                ],
                clip_on=True,
                zorder=6,
            )
        bottom = bottom + h

    ax_bot.set_ylabel("拨打量（通次）", fontsize=11, fontweight="bold", color=chart_theme.TEXT_PRIMARY)
    ax_bot.tick_params(axis="y", which="both", left=False, labelleft=False)
    ax_bot.set_xticks(x)
    ax_bot.set_xticklabels(
        [_week_label(*week_keys[i]) for i in range(n)],
        rotation=0,
        ha="center",
        fontsize=WEEK_TICK_FS,
    )
    ax_bot.grid(True, axis="y", alpha=0.85, linestyle="--")
    ax_bot.set_xlim(x.min() - 0.5, x.max() + 0.5)
    chart_theme.polish_ax_bar_containers(ax_bot, stacked=True)

    fig.suptitle(
        "拨打模式周度接通率与拨打量（按 call_type）",
        fontsize=TITLE_FS,
        fontweight="bold",
        y=title_y,
        va="top",
        color=chart_theme.TEXT_PRIMARY,
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    chart_theme.save_figure(fig, str(OUT_PATH), dpi=DPI)
    plt.close(fig)
    print(f"[OK] {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
