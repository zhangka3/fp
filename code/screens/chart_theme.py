# -*- coding: utf-8 -*-
"""周报图表统一视觉主题（Matplotlib）。各 screen_*.py 在 import 后调用 apply_chart_theme()。"""

from __future__ import annotations

import matplotlib

# 对齐可读性：浅底深字（参考 UI/UX Pro Max 对比度建议）
TEXT_PRIMARY = "#0F172A"
TEXT_MUTED = "#64748B"
GRID_COLOR = "#E2E8F0"
SPINE_COLOR = "#CBD5E1"
FIG_FACE = "#FFFFFF"
LEGEND_FACE = "#F8FAFC"
# Dashboard：卡片式浅色绘图区（现代 BI 面板底）
AXES_PANEL = "#F8FAFC"

# visual_style: "dashboard" | "classic"
VISUAL_STYLE = "dashboard"

# 多月份序列色（柱条用偏浅马卡龙 / pastel，避免压在浅灰面板上过重）
MONTH_ACCENT = [
    "#CBD5E1",
    "#BFDBFE",
    "#A5F3FC",
    "#C4B5FD",
    "#FBCFE8",
    "#FDE68A",
]

# 多月份折线专用：色相与明度拉开，避免与浅色柱图混淆
MONTH_LINE_COLORS = [
    "#1D4ED8",
    "#B91C1C",
    "#047857",
    "#B45309",
    "#6D28D9",
    "#BE185D",
    "#0E7490",
    "#A16207",
]

# GRP：同一 collector_ins 堆叠柱用浅色、回款率折线用同系深色（索引一一对应）
GRP_BAR_LINE_PAIRS: list[tuple[str, str]] = [
    ("#FECACA", "#991B1B"),
    ("#BFDBFE", "#1E3A8A"),
    ("#BBF7D0", "#166534"),
    ("#FDE68A", "#A16207"),
    ("#DDD6FE", "#5B21B6"),
    ("#FBCFE8", "#9D174D"),
    ("#A5F3FC", "#115E59"),
    ("#FED7AA", "#9A3412"),
    ("#E9D5FF", "#6B21A8"),
    ("#D9F99D", "#3F6212"),
    ("#CFFAFE", "#164E63"),
    ("#FECDD3", "#9F1239"),
    ("#E2E8F0", "#1E293B"),
    ("#F5D0FE", "#86198F"),
    ("#BAE6FD", "#075985"),
    ("#7DD3FC", "#0369A1"),
]


def grp_bar_line_for_series(idx: int) -> tuple[str, str]:
    """返回 (堆叠柱颜色, 折线颜色)，idx 与 collectors 枚举顺序一致。"""
    bar_c, line_c = GRP_BAR_LINE_PAIRS[idx % len(GRP_BAR_LINE_PAIRS)]
    return bar_c, line_c


# 多系列堆叠（非 GRP 成对逻辑时仍可用）：浅色但仍可区分（Tailwind 200～300 档）
SERIES_COLORS = [
    "#93C5FD",
    "#67E8F9",
    "#86EFAC",
    "#FDE047",
    "#FDBA74",
    "#D8B4FE",
    "#F9A8D4",
    "#A5B4FC",
    "#5EEAD4",
    "#FCD34D",
    "#FCA5A5",
    "#C4B5FD",
    "#BBF7D0",
    "#DDD6FE",
]

# M0：左轴体量柱 + 右轴语义线（柱再淡一档）
M0_VOLUME_BAR = "#E2E8F0"
M0_OVERDUE_LINE = "#DC2626"
M0_COUNT_LINE = "#EA580C"
M0_COLLECTION_7D = "#16A34A"
M0_COLLECTION_30D = "#7C3AED"
M0_IND1_LINE = "#2563EB"
# 单量逾期图左轴柱色（与金额图区分）
M0_BAR_ALT = "#DBEAFE"
# 按周多线催回率
M0_WEEKLY_LINE_MAP = {
    "1d": "#DC2626",
    "3d": "#EA580C",
    "7d": "#059669",
    "15d": "#2563EB",
    "30d": "#7C3AED",
}

# 环比/增减柱（稍浅，仍为「好/坏」语义）
DIFF_POSITIVE = "#6EE7B7"
DIFF_NEGATIVE = "#FCA5A5"

LAST_POINT_MARKER = TEXT_PRIMARY
ANNOTATE_COLOR = TEXT_PRIMARY


def month_color_dict(month_keys: list[str] | tuple[str, ...]) -> dict[str, str]:
    months = sorted(set(month_keys))
    return {m: MONTH_ACCENT[i % len(MONTH_ACCENT)] for i, m in enumerate(months)}


def month_line_color_dict(month_keys: list[str] | tuple[str, ...]) -> dict[str, str]:
    """折线图多月份序列色（对比度高于 MONTH_ACCENT）。"""
    months = sorted(set(month_keys))
    return {m: MONTH_LINE_COLORS[i % len(MONTH_LINE_COLORS)] for i, m in enumerate(months)}


def month_label_cn(ym: str) -> str:
    if ym and len(ym) >= 7 and ym[4] == "-":
        try:
            return f"{int(ym[5:7])}月"
        except ValueError:
            return ym
    return ym


def _rc_classic() -> None:
    matplotlib.rcParams.update(
        {
            "font.sans-serif": [
                "SimHei",
                "Microsoft YaHei",
                "DengXian",
                "DejaVu Sans",
            ],
            "axes.unicode_minus": False,
            "figure.facecolor": FIG_FACE,
            "axes.facecolor": FIG_FACE,
            "axes.edgecolor": SPINE_COLOR,
            "axes.labelcolor": TEXT_PRIMARY,
            "axes.titlecolor": TEXT_PRIMARY,
            "axes.linewidth": 0.8,
            "xtick.color": TEXT_MUTED,
            "ytick.color": TEXT_MUTED,
            "grid.color": GRID_COLOR,
            "grid.alpha": 0.9,
            "grid.linestyle": "--",
            "grid.linewidth": 0.6,
            "legend.frameon": True,
            "legend.framealpha": 0.96,
            "legend.edgecolor": SPINE_COLOR,
            "legend.facecolor": LEGEND_FACE,
            "axes.grid": True,
            "axes.axisbelow": True,
        }
    )


def _rc_dashboard() -> None:
    """现代 Dashboard / BI：白画布 + 浅灰面板、水平参考线为主。"""
    matplotlib.rcParams.update(
        {
            "font.sans-serif": [
                "SimHei",
                "Microsoft YaHei",
                "DengXian",
                "DejaVu Sans",
            ],
            "axes.unicode_minus": False,
            "figure.facecolor": FIG_FACE,
            "axes.facecolor": AXES_PANEL,
            "axes.edgecolor": "#E2E8F0",
            "axes.labelcolor": TEXT_PRIMARY,
            "axes.titlecolor": TEXT_PRIMARY,
            "axes.linewidth": 1.0,
            "xtick.color": TEXT_MUTED,
            "ytick.color": TEXT_MUTED,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID_COLOR,
            "grid.alpha": 1.0,
            "grid.linestyle": "-",
            "grid.linewidth": 0.75,
            "legend.frameon": True,
            "legend.framealpha": 1.0,
            "legend.edgecolor": SPINE_COLOR,
            "legend.facecolor": FIG_FACE,
        }
    )


def apply_chart_theme() -> None:
    if VISUAL_STYLE == "dashboard":
        _rc_dashboard()
    else:
        _rc_classic()


def style_axes_light(ax, *, grid_axis: str = "y") -> None:
    ax.tick_params(axis="both", colors=TEXT_MUTED, labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(SPINE_COLOR)
    ax.spines["bottom"].set_color(SPINE_COLOR)
    if VISUAL_STYLE == "dashboard":
        if grid_axis in ("y", "both"):
            ax.grid(True, axis="y", color=GRID_COLOR, linestyle="-", linewidth=0.75, alpha=1.0)
        if grid_axis in ("x", "both"):
            ax.grid(True, axis="x", color=GRID_COLOR, linestyle="-", linewidth=0.5, alpha=0.65)
    else:
        if grid_axis in ("y", "both"):
            ax.grid(True, axis="y", alpha=0.85)
        if grid_axis in ("x", "both"):
            ax.grid(True, axis="x", alpha=0.5)


# --- 纯表图（S/M1 recovery & assignment table）统一视觉 ---
# 画布留白：表体略缩，外圈浅灰「卡片」感（y0 略抬高，便于与标题收紧间距）
TABLE_AX_BBOX = (0.035, 0.058, 0.93, 0.848)
# 六张纯表图共用标题样式（字号 / 字重 / 与表格间距）
SCREEN_TABLE_TITLE_FONTSIZE = 20
SCREEN_TABLE_TITLE_PAD = 4
# S 类双表头：第一行分组带（与第二行月份列对齐）
TABLE_S_GROUP_HEAD = ("#BFDBFE", "#C7D2FE", "#E9D5FF")  # S1 / S2 / S3 第一行
TABLE_S_GROUP_MONTH = ("#DBEAFE", "#EEF2FF", "#F3E8FF")  # 第二行月份列组
# M1 热力：低→高（极淡，避免抢字）
TABLE_HEAT_LOW = "#EFF6FF"
TABLE_HEAT_HIGH = "#DCFCE7"


def _lerp_hex(c_low: str, c_high: str, t: float) -> str:
    import matplotlib.colors as mcolors

    t = max(0.0, min(1.0, float(t)))
    a = mcolors.to_rgb(c_low)
    b = mcolors.to_rgb(c_high)
    rgb = tuple(a[i] + t * (b[i] - a[i]) for i in range(3))
    return mcolors.to_hex(rgb)


def table_percent_heatmap_facecolor(value: float, vmin: float, vmax: float) -> str:
    """按百分比数值在 [vmin,vmax] 上线性插值背景色（仅背景，字色仍用 TEXT_PRIMARY）。"""
    if vmax <= vmin:
        return FIG_FACE
    return _lerp_hex(TABLE_HEAT_LOW, TABLE_HEAT_HIGH, (value - vmin) / (vmax - vmin))


def prepare_screen_table_figure(fig, ax) -> None:
    """表图外圈浅底 + 内区白底，与 dashboard 主题一致。"""
    fig.patch.set_facecolor(AXES_PANEL if VISUAL_STYLE == "dashboard" else FIG_FACE)
    ax.set_facecolor(FIG_FACE)
    ax.axis("tight")
    ax.axis("off")


def style_screen_table_s_headers(
    table,
    *,
    ncol: int,
    font_prop,
) -> None:
    """S 类双行表头：第一行 S1/S2/S3 分组带 + 第二行月份。

    列布局与 `screen_s_class` 一致：row2 为 Day(0) + S1 三月(1–3) + S2 三月(4–6) + S3 三月(7–9)；
    row1 为 ['','',S1,'','',S2,'','',S3,'']，即 S1/S2/S3 分别压在对应三月列的中间列(2/5/8)上。
    第一行色带必须与 1–3、4–6、7–9 对齐（不可误用 2–4 等，否则会与月份列错位）。
    """
    fm = font_prop
    hide = {"color": FIG_FACE, "fontproperties": fm}

    # 第一行
    for col in range(ncol):
        cell = table[(0, col)]
        cell.set_height(0.026)
        cell.set_linewidth(0.9)
        cell.set_edgecolor(SPINE_COLOR)
        if col == 0:
            cell.set_facecolor(FIG_FACE)
            cell.set_text_props(**hide)
        elif 1 <= col <= 3:
            face = TABLE_S_GROUP_HEAD[0]
            cell.set_facecolor(face)
            if col == 2:
                cell.set_text_props(
                    weight="bold",
                    color=TEXT_PRIMARY,
                    fontproperties=fm,
                    fontsize=14,
                )
            else:
                cell.set_text_props(color=face, fontproperties=fm)
        elif 4 <= col <= 6:
            face = TABLE_S_GROUP_HEAD[1]
            cell.set_facecolor(face)
            if col == 5:
                cell.set_text_props(
                    weight="bold",
                    color=TEXT_PRIMARY,
                    fontproperties=fm,
                    fontsize=14,
                )
            else:
                cell.set_text_props(color=face, fontproperties=fm)
        elif 7 <= col <= 9:
            face = TABLE_S_GROUP_HEAD[2]
            cell.set_facecolor(face)
            if col == 8:
                cell.set_text_props(
                    weight="bold",
                    color=TEXT_PRIMARY,
                    fontproperties=fm,
                    fontsize=14,
                )
            else:
                cell.set_text_props(color=face, fontproperties=fm)
        else:
            cell.set_facecolor(FIG_FACE)
            cell.set_text_props(**hide)

    # 第二行：Day + 三组月份列染色
    for col in range(ncol):
        cell = table[(1, col)]
        cell.set_height(0.024)
        cell.set_linewidth(0.85)
        cell.set_edgecolor(SPINE_COLOR)
        if col == 0:
            cell.set_facecolor("#F1F5F9")
        elif 1 <= col <= 3:
            cell.set_facecolor(TABLE_S_GROUP_MONTH[0])
        elif 4 <= col <= 6:
            cell.set_facecolor(TABLE_S_GROUP_MONTH[1])
        else:
            cell.set_facecolor(TABLE_S_GROUP_MONTH[2])
        cell.set_text_props(
            weight="bold",
            fontproperties=fm,
            fontsize=10,
            color=TEXT_PRIMARY,
        )


def style_screen_table_simple_header(
    table,
    *,
    ncol: int,
    row_index: int,
    font_prop,
    fontsize: int = 11,
) -> None:
    """单行表头（M1）。"""
    for col in range(ncol):
        cell = table[(row_index, col)]
        cell.set_facecolor("#E8EEF4")
        cell.set_height(0.028)
        cell.set_linewidth(0.9)
        cell.set_edgecolor(SPINE_COLOR)
        cell.set_text_props(
            weight="bold",
            fontproperties=font_prop,
            fontsize=fontsize,
            color=TEXT_PRIMARY,
        )


def style_screen_table_body(
    table,
    *,
    data_row_start: int,
    nrows: int,
    ncol: int,
    font_prop,
    day_col: int = 0,
    percent_cols: frozenset[int],
    data_fontsize: int = 8,
    heatmap_values: list[list[float | None]] | None = None,
    heatmap_vmin: float | None = None,
    heatmap_vmax: float | None = None,
) -> None:
    """
    数据区：Day 列强调；百分比列右对齐；可选按行热力（与斑马纹二选一：有数值用热力图底色）。
    heatmap_values: 仅数据行，长度 = nrows - data_row_start，每行 ncol，与 table 行列对齐。
    """
    for row in range(data_row_start, nrows):
        dr = row - data_row_start
        zebra = (dr % 2 == 0)
        for col in range(ncol):
            cell = table[(row, col)]
            cell.set_height(0.02)
            cell.set_fontsize(data_fontsize)
            cell.set_linewidth(0.55)
            cell.set_edgecolor(GRID_COLOR)

            ha = "right" if col in percent_cols else "center"
            cell.get_text().set_horizontalalignment(ha)

            use_heat = False
            bg = FIG_FACE if zebra else "#F8FAFC"
            if heatmap_values is not None and heatmap_vmin is not None and heatmap_vmax is not None:
                if 0 <= dr < len(heatmap_values) and col < len(heatmap_values[dr]):
                    v = heatmap_values[dr][col]
                    if v is not None and col in percent_cols:
                        bg = table_percent_heatmap_facecolor(v, heatmap_vmin, heatmap_vmax)
                        use_heat = True

            if col == day_col:
                cell.set_text_props(weight="bold", fontproperties=font_prop, color=TEXT_PRIMARY)
                cell.set_facecolor("#F1F5F9")
            else:
                if not use_heat:
                    bg = FIG_FACE if zebra else "#F8FAFC"
                cell.set_text_props(fontproperties=font_prop, color=TEXT_PRIMARY)
                cell.set_facecolor(bg)


def save_figure(
    fig,
    path,
    *,
    dpi: int = 150,
    tight: bool = True,
    pad: float = 0.2,
    save_facecolor: str | None = None,
) -> None:
    """save_facecolor：默认白底；表图等可传 AXES_PANEL 以保留外圈浅灰卡片感。"""
    fc = save_facecolor if save_facecolor is not None else FIG_FACE
    kw: dict = {"dpi": dpi, "facecolor": fc, "edgecolor": "none"}
    if tight:
        kw["bbox_inches"] = "tight"
        kw["pad_inches"] = pad
    fig.savefig(path, **kw)


def font_prop_dengxian():
    from matplotlib import font_manager

    return font_manager.FontProperties(family="DengXian")


def screen_table_title_fontprop():
    """S/M1 六张对比表标题：等线加粗、偏大字号。"""
    from matplotlib import font_manager

    return font_manager.FontProperties(
        family="DengXian",
        weight="bold",
        size=SCREEN_TABLE_TITLE_FONTSIZE,
    )


def set_screen_table_title(ax, text: str) -> None:
    ax.set_title(
        text,
        fontproperties=screen_table_title_fontprop(),
        pad=SCREEN_TABLE_TITLE_PAD,
        color=TEXT_PRIMARY,
    )


def polish_bar_patches(
    patches,
    *,
    shadow: bool = True,
    shadow_offset: tuple[float, float] = (2.2, -2.2),
    shadow_alpha: float = 0.26,
) -> None:
    """给柱条增加落地阴影（SimplePatchShadow），略抬层次感。"""
    if not shadow or not patches:
        return
    from matplotlib import patheffects as pe

    for p in patches:
        p.set_path_effects(
            [
                pe.SimplePatchShadow(
                    offset=shadow_offset,
                    alpha=shadow_alpha,
                    shadow_rgbFace="#0f172a",
                    rho=0.35,
                ),
                pe.Normal(),
            ]
        )


def polish_ax_bar_containers(ax, *, shadow: bool = True, stacked: bool = False) -> None:
    """对当前 axes 上所有 BarContainer 做阴影（堆叠图用更淡阴影避免发糊）。"""
    from matplotlib.container import BarContainer

    if VISUAL_STYLE == "dashboard":
        alpha = 0.07 if stacked else 0.14
    else:
        alpha = 0.14 if stacked else 0.26
    for c in ax.containers:
        if isinstance(c, BarContainer) and getattr(c, "patches", None):
            polish_bar_patches(c.patches, shadow=shadow, shadow_alpha=alpha)


def polish_line2d(
    line,
    *,
    stroke_extra: float = 2.8,
    stroke_color: str | None = None,
    stroke_alpha: float = 0.92,
    marker_edge_boost: float = 0.35,
) -> None:
    """折线底层白描边 + Normal，减轻与网格/柱重叠时的发虚；略加强 marker 白边。"""
    from matplotlib import patheffects as pe
    from matplotlib.lines import Line2D

    if not isinstance(line, Line2D):
        return
    if stroke_color is None:
        stroke_color = FIG_FACE if VISUAL_STYLE == "dashboard" else "#FFFFFF"
    w = float(line.get_linewidth() or 1.5) + stroke_extra
    line.set_path_effects(
        [
            pe.Stroke(linewidth=w, foreground=stroke_color, alpha=stroke_alpha),
            pe.Normal(),
        ]
    )
    m = line.get_marker()
    if m and str(m).lower() not in ("none", ""):
        line.set_markeredgewidth(
            float(line.get_markeredgewidth() or 1.0) + marker_edge_boost
        )
        mec = line.get_markeredgecolor()
        if mec in (None, "none", "auto"):
            line.set_markeredgecolor(FIG_FACE if VISUAL_STYLE == "dashboard" else "#FFFFFF")


def polish_ax_lines(ax, *, stroke_extra: float = 2.8) -> None:
    for ln in ax.get_lines():
        polish_line2d(ln, stroke_extra=stroke_extra)


def polish_twin_bars_and_lines(ax_bar, ax_line, *, stacked_bars: bool = False) -> None:
    """左轴柱 + 右轴线（常见于 M0 / S 类 / M1）。"""
    polish_ax_bar_containers(ax_bar, stacked=stacked_bars)
    polish_ax_lines(ax_line)
