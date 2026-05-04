#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
满频率 / 有效接通率 / 案均拨打 / 案均有效通时（full_call.json，最近 5 周）

规则要点：
- 每个 case_type 单独一条折线，只在「该类型自己的 5 个周点」上连线，不跨类型。
- 下图每个 case_type 下按周各一根柱（该周 *_dif），周与周可不同。
- 若某 case_type 在「全局最近一周」无数据，则整类不展示。
- 上图仅在「最近 3 周」的点上标注具体数值：满频/接通率为「%」；案均拨打为「次/案」；案均有效通时为「秒/案」（与数仓 duration 口径一致）；无框、无底；率类下图柱为 pp，案均拨打/通时柱为对应单位周差。
- 纵轴不显示刻度数字；横轴刻度与标签仅在第三带（整体）的下图展示。
- `case_type` 标题置于**上子图轴框上方**（数据坐标 + 轴外 y），不压在折线/数值标注上。
"""

from __future__ import annotations

import json
import re
import sys
import io
import unicodedata
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import numpy as np

import chart_theme

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

chart_theme.apply_chart_theme()

NUM_WEEKS = 5
ANNOTATE_LAST_WEEKS = 3
GAP_BETWEEN_GROUPS = 2
# 大标题下沿与作图区上沿间距（厘米 → 按图高换算为 figure 归一化高度）
TITLE_TO_CHART_GAP_CM = 0.5
TITLE_FONTSIZE = 22


def _safe_float(val):
    if val is None or val == "NULL" or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


_RANK_SUFFIX = re.compile(r"-(RA|RB|RC|RD)$", re.IGNORECASE)


def _case_type_sort_key(ct: str) -> tuple:
    """
    横轴分组顺序：S1→S2→S3；再 M2→M2+→M4+→M5+（按 M 后数字升序，同档「无 +」先于「+」）；
    组内 RA→RB→RC→RD。用末尾 ``-RA``/``-RB`` 等解析，避免 ``M2+-RB`` 被 ``rsplit`` 拆错。
    """
    raw = unicodedata.normalize("NFKC", (ct or "").strip()).replace("＋", "+")
    if not raw:
        return (99, 99, 99, 9, "")
    m = _RANK_SUFFIX.search(raw)
    if not m:
        return (99, 99, 99, 9, raw)
    rk = m.group(1).upper()
    fam = raw[: m.start()].rstrip("-").strip()
    fam_u = fam.upper()

    rk_order = {"RA": 1, "RB": 2, "RC": 3, "RD": 4}.get(rk, 9)

    sm = re.fullmatch(r"S([123])", fam_u)
    if sm:
        return (0, int(sm.group(1)), 0, rk_order, raw)

    mm = re.fullmatch(r"M(\d+)(\+)?", fam_u)
    if mm:
        major = int(mm.group(1))
        plus_rank = 1 if mm.group(2) else 0  # 同档 M2 先于 M2+
        return (1, major, plus_rank, rk_order, raw)

    return (2, 0, 0, rk_order, raw)


def _week_label(y: int, w: int) -> str:
    return f"{y}-W{w:02d}"


def _load_indexed(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    header = data["header"]
    idx = {h: i for i, h in enumerate(header)}
    need = [
        "year",
        "weeknum",
        "case_type",
        "self_full_rate",
        "self_full_rate_dif",
        "contact_full_rate",
        "contact_full_rate_dif",
        "total_full_rate",
        "total_full_rate_dif",
        "eff_self_con_rate",
        "eff_self_con_rate_dif",
        "eff_cont_con_rate",
        "eff_cont_con_rate_dif",
        "eff_con_rate",
        "eff_con_rate_dif",
        "avg_self_call_cnt_per_case",
        "avg_self_call_cnt_per_case_dif",
        "avg_noself_call_cnt_per_case",
        "avg_noself_call_cnt_per_case_dif",
        "avg_call_cnt_per_case",
        "avg_call_cnt_per_case_dif",
        "avg_self_dur_per_case",
        "avg_self_dur_per_case_dif",
        "avg_noself_dur_per_case",
        "avg_noself_dur_per_case_dif",
        "avg_dur_per_case",
        "avg_dur_per_case_dif",
    ]
    for k in need:
        if k not in idx:
            raise SystemExit(f"full_call.json 缺少列: {k}")
    rows = []
    for row in data["rows"]:
        d = {k: row[idx[k]] for k in need}
        d["_y"] = int(str(d["year"]).strip())
        d["_w"] = int(str(d["weeknum"]).strip())
        rows.append(d)
    return header, rows


def _latest_week_keys(rows: list[dict]) -> list[tuple[int, int]]:
    keys = sorted({(r["_y"], r["_w"]) for r in rows})
    return keys[-NUM_WEEKS:] if len(keys) >= NUM_WEEKS else keys


def _filter_weeks(rows: list[dict], week_keys: list[tuple[int, int]]) -> list[dict]:
    allow = set(week_keys)
    return [r for r in rows if (r["_y"], r["_w"]) in allow]


def _ordered_case_types(rows: list[dict]) -> list[str]:
    return sorted({r["case_type"] for r in rows if r.get("case_type")}, key=_case_type_sort_key)


def _build_week_ct_map(rows: list[dict]) -> dict[tuple[int, int], dict[str, dict]]:
    m: dict[tuple[int, int], dict[str, dict]] = defaultdict(dict)
    for r in rows:
        m[(r["_y"], r["_w"])][r["case_type"]] = r
    return m


def _case_types_with_latest(
    case_types_all: list[str],
    latest: tuple[int, int],
    rows_by_week_ct: dict[tuple[int, int], dict[str, dict]],
) -> list[str]:
    """最近一周无该 case_type 则不展示。"""
    return [ct for ct in case_types_all if rows_by_week_ct.get(latest, {}).get(ct)]


def _hide_y_ticklabels(ax):
    ax.tick_params(axis="y", which="both", left=True, labelleft=False)


def _draw_one_figure(
    suptitle: str,
    specs: list[tuple[str, str, str]],
    fname: str,
    out_dir: Path,
    week_keys: list[tuple[int, int]],
    case_types: list[str],
    rows_by_week_ct: dict[tuple[int, int], dict[str, dict]],
    ylabel_pct: str,
    *,
    line_scale: float = 100.0,
    dif_scale: float = 100.0,
    annotate_as_percent: bool = True,
    dif_ylabel: str | None = None,
):
    annotate_weeks = week_keys[-ANNOTATE_LAST_WEEKS:] if len(week_keys) >= ANNOTATE_LAST_WEEKS else week_keys

    x_of: dict[tuple[str, tuple[int, int]], float] = {}
    cur = 0.0
    for ct in case_types:
        for wk in week_keys:
            x_of[(ct, wk)] = cur
            cur += 1.0
        cur += GAP_BETWEEN_GROUPS

    all_ticks = [x_of[(ct, wk)] for ct in case_types for wk in week_keys]
    x_min = min(all_ticks) - 0.5 if all_ticks else 0
    x_max = max(all_ticks) + 0.5 if all_ticks else 1

    fig = plt.figure(figsize=(24, 16))
    fh_in = float(fig.get_figheight())
    gap_frac = (TITLE_TO_CHART_GAP_CM / 2.54) / fh_in
    # suptitle 用 va=top：y 为标题顶；标题大致高度（英寸）/ 图高 → 归一化
    cap_frac = (TITLE_FONTSIZE * 1.2 / 72.0) / fh_in
    title_y = 0.998
    top_axes = title_y - cap_frac - gap_frac
    top_axes = max(0.58, min(top_axes, 0.97))
    outer = fig.add_gridspec(
        3, 1, hspace=0.16, left=0.055, right=0.99, top=top_axes, bottom=0.06
    )

    for band_i, (rate_col, dif_col, band_title) in enumerate(specs):
        inner = outer[band_i].subgridspec(2, 1, height_ratios=[2, 1], hspace=0.025)
        ax1 = fig.add_subplot(inner[0, 0])
        ax2 = fig.add_subplot(inner[1, 0])

        y_max = float("-inf")
        y_min = float("inf")
        colors = chart_theme.SERIES_COLORS

        for ci, ct in enumerate(case_types):
            xs = [x_of[(ct, wk)] for wk in week_keys]
            ys = []
            for wk in week_keys:
                cell = rows_by_week_ct.get(wk, {}).get(ct)
                v = _safe_float(cell[rate_col]) if cell else None
                ys.append(v * line_scale if v is not None else np.nan)
            color = colors[ci % len(colors)]
            ax1.plot(
                xs,
                ys,
                color=color,
                linewidth=2.6,
                marker="o",
                markersize=5,
                markeredgecolor="white",
                markeredgewidth=0.9,
                alpha=0.92,
            )
            arr = np.array(ys, dtype=float)
            arr = arr[np.isfinite(arr)]
            if arr.size:
                y_max = max(y_max, float(arr.max()))
                y_min = min(y_min, float(arr.min()))

            for wk in annotate_weeks:
                cell = rows_by_week_ct.get(wk, {}).get(ct)
                if not cell:
                    continue
                xv = x_of[(ct, wk)]
                rv = _safe_float(cell[rate_col])
                if rv is None:
                    continue
                yv = rv * line_scale
                ann = f"{yv:.2f}%" if annotate_as_percent else f"{yv:.2f}"
                ax1.annotate(
                    ann,
                    xy=(xv, yv),
                    xytext=(0, 10),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=6,
                    color=chart_theme.TEXT_PRIMARY,
                    bbox=None,
                )

        for gi, ct in enumerate(case_types):
            xs_g = [x_of[(ct, wk)] for wk in week_keys]
            x0, x1 = min(xs_g) - 0.45, max(xs_g) + 0.45
            bg = "#F8FAFC" if gi % 2 == 0 else chart_theme.FIG_FACE
            ax1.axvspan(x0, x1, facecolor=bg, alpha=0.55, zorder=0)
            ax2.axvspan(x0, x1, facecolor=bg, alpha=0.55, zorder=0)
            xm = (x0 + x1) / 2.0
            # case_type 放在上子图「绘图区之上」（x 数据坐标 + y 轴外上方），避免挡折线标注
            trans = mtransforms.blended_transform_factory(ax1.transData, ax1.transAxes)
            ax1.text(
                xm,
                1.02,
                ct,
                transform=trans,
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
                color=chart_theme.TEXT_PRIMARY,
                clip_on=False,
                zorder=20,
            )

        bar_w = min(0.62, 0.9 * (1.0 - 0.08))
        for ct in case_types:
            xs_b, hs, cs = [], [], []
            for wk in week_keys:
                xv = x_of[(ct, wk)]
                cell = rows_by_week_ct.get(wk, {}).get(ct)
                raw = _safe_float(cell[dif_col]) if cell else None
                h = (raw * dif_scale) if raw is not None else 0.0
                xs_b.append(xv)
                hs.append(h)
                cs.append(chart_theme.DIFF_POSITIVE if h >= 0 else chart_theme.DIFF_NEGATIVE)
            ax2.bar(xs_b, hs, width=bar_w, color=cs, alpha=0.88)
            for wk, xv, h in zip(week_keys, xs_b, hs):
                if wk in annotate_weeks and abs(h) > 1e-6:
                    ax2.text(
                        xv,
                        h + (0.08 if h >= 0 else -0.08),
                        f"{h:+.2f}",
                        ha="center",
                        va="bottom" if h >= 0 else "top",
                        fontsize=6,
                        fontweight="bold",
                    )

        ax1.set_xticks([])
        ax1.set_xlim(x_min, x_max)
        ax2.set_xlim(x_min, x_max)

        ax1.set_ylabel(f"{band_title}\n{ylabel_pct}", fontsize=10, fontweight="bold")
        ax2.set_ylabel(
            dif_ylabel if dif_ylabel is not None else "环比差 (pp)",
            fontsize=9,
            fontweight="bold",
        )
        ax1.grid(True, axis="y", alpha=0.85, linestyle="--")
        ax2.grid(True, axis="y", alpha=0.85, linestyle="--")
        ax2.axhline(0, color=chart_theme.TEXT_MUTED, linewidth=1, alpha=0.75)

        if np.isfinite(y_max) and np.isfinite(y_min) and y_max > y_min:
            lo = max(0.0, y_min * 0.88)
            hi = y_max * 1.22
        else:
            lo, hi = 0.0, 1.0
        ax1.set_ylim(lo, hi)

        _hide_y_ticklabels(ax1)
        _hide_y_ticklabels(ax2)

        if band_i == 2:
            ax2.set_xticks(all_ticks)
            ax2.set_xticklabels(
                [_week_label(*wk) for ct in case_types for wk in week_keys],
                rotation=90,
                fontsize=7,
                ha="center",
            )
        else:
            ax2.set_xticks([])
            ax2.set_xticklabels([])

        chart_theme.polish_ax_lines(ax1, stroke_extra=2.0)
        chart_theme.polish_ax_bar_containers(ax2, stacked=False)

    fig.suptitle(
        f"{suptitle}（最近 {len(week_keys)} 周；标注为最近 {len(annotate_weeks)} 周）",
        fontsize=TITLE_FONTSIZE,
        fontweight="bold",
        y=title_y,
        va="top",
        color=chart_theme.TEXT_PRIMARY,
    )
    out_path = out_dir / fname
    chart_theme.save_figure(fig, str(out_path), dpi=150)
    plt.close(fig)
    print(f"[OK] {out_path}")


def run_charts(data_path: Path, out_dir: Path) -> None:
    _, dict_rows = _load_indexed(data_path)
    week_keys = _latest_week_keys(dict_rows)
    if not week_keys:
        raise SystemExit("full_call 无可用周键")
    rows = _filter_weeks(dict_rows, week_keys)
    rows_by_week_ct = _build_week_ct_map(rows)
    latest = week_keys[-1]
    case_types_all = _ordered_case_types(rows)
    case_types = _case_types_with_latest(case_types_all, latest, rows_by_week_ct)
    if not case_types:
        raise SystemExit("full_call：最近一周无任何 case_type 数据，无法作图")

    _draw_one_figure(
        "满频率（按 case_type 周内连线）及周环比柱",
        [
            ("self_full_rate", "self_full_rate_dif", "本人满频率"),
            ("contact_full_rate", "contact_full_rate_dif", "非本人满频率"),
            ("total_full_rate", "total_full_rate_dif", "整体满频率"),
        ],
        "full_call_full_rates.png",
        out_dir,
        week_keys,
        case_types,
        rows_by_week_ct,
        "满频率 (%)",
    )
    _draw_one_figure(
        "案均拨打次数（按 case_type 周内连线）及周环比柱",
        [
            ("avg_self_call_cnt_per_case", "avg_self_call_cnt_per_case_dif", "本人案均拨打"),
            ("avg_noself_call_cnt_per_case", "avg_noself_call_cnt_per_case_dif", "非本人案均拨打"),
            ("avg_call_cnt_per_case", "avg_call_cnt_per_case_dif", "整体案均拨打"),
        ],
        "full_call_avg_calls_per_case.png",
        out_dir,
        week_keys,
        case_types,
        rows_by_week_ct,
        "次/案",
        line_scale=1.0,
        dif_scale=1.0,
        annotate_as_percent=False,
        dif_ylabel="环比差 (次/案)",
    )
    _draw_one_figure(
        "案均有效通时（按 case_type 周内连线）及周环比柱",
        [
            ("avg_self_dur_per_case", "avg_self_dur_per_case_dif", "本人案均有效通时"),
            ("avg_noself_dur_per_case", "avg_noself_dur_per_case_dif", "非本人案均有效通时"),
            ("avg_dur_per_case", "avg_dur_per_case_dif", "整体案均有效通时"),
        ],
        "full_call_avg_dur_per_case.png",
        out_dir,
        week_keys,
        case_types,
        rows_by_week_ct,
        "秒/案",
        line_scale=1.0,
        dif_scale=1.0,
        annotate_as_percent=False,
        dif_ylabel="环比差 (秒/案)",
    )
    _draw_one_figure(
        "有效接通率（按 case_type 周内连线）及周环比柱",
        [
            ("eff_self_con_rate", "eff_self_con_rate_dif", "本人有效接通率"),
            ("eff_cont_con_rate", "eff_cont_con_rate_dif", "非本人有效接通率"),
            ("eff_con_rate", "eff_con_rate_dif", "整体有效接通率"),
        ],
        "full_call_eff_rates.png",
        out_dir,
        week_keys,
        case_types,
        rows_by_week_ct,
        "接通率 (%)",
    )


if __name__ == "__main__":
    _ROOT = Path(__file__).resolve().parent.parent.parent
    data_p = _ROOT / "data" / "full_call.json"
    out_d = _ROOT / "screenshots"
    out_d.mkdir(parents=True, exist_ok=True)
    if not data_p.exists():
        print(f"[SKIP] 缺少 {data_p}")
        sys.exit(0)
    run_charts(data_p, out_d)
