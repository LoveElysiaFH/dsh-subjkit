# -*- coding: utf-8 -*-
"""数学图示：函数图像、平面几何、数轴、韦恩图。"""
from __future__ import annotations

import numpy as np
from matplotlib.patches import Arc, Circle, Rectangle
from matplotlib.ticker import MultipleLocator

from .base import GREY, INK, LIGHT, label, new_figure, poly, unit
# 表达式解析搬到了 expr.py（补乘号 + 中文报错）；这里保留同名导出，
# 免得 `from .mathfig import make_fn` 的老代码断掉。
from .expr import FUNCS, ExprError, compile_expr, make_fn  # noqa: F401


_LEGEND_BOXES = {
    "upper right": (0.58, 0.66, 1.00, 1.00),
    "upper left": (0.00, 0.66, 0.42, 1.00),
    "lower right": (0.58, 0.00, 1.00, 0.34),
    "lower left": (0.00, 0.00, 0.42, 0.34),
}


def _pick_legend(ax, samples, pts) -> str:
    """`legend: auto` 用：挑一个曲线和点最少的角，避免图例压在抛物线上。"""
    (x0, x1) = ax.get_xlim()
    (y0, y1) = ax.get_ylim()
    w = max(float(x1) - float(x0), 1e-9)
    h = max(float(y1) - float(y0), 1e-9)

    def frac(x, y):
        return (float(x) - float(x0)) / w, (float(y) - float(y0)) / h

    best, best_score = "upper right", None
    for name, (bx0, by0, bx1, by1) in _LEGEND_BOXES.items():
        score = 0
        for sx, sy in samples:
            fx, fy = frac(sx, sy)
            if bx0 <= fx <= bx1 and by0 <= fy <= by1:
                score += 1
        for p in pts:                      # 点标签比曲线更怕压
            fx, fy = frac(p["x"], p["y"])
            if bx0 <= fx <= bx1 and by0 <= fy <= by1:
                score += 40
        if best_score is None or score < best_score:
            best, best_score = name, score
    return best


def plot(spec: dict):
    fig, ax = new_figure(*spec.get("size", [5.8, 3.6]), equal=False)
    # new_figure 默认整个关掉坐标轴；函数图像要有刻度，所以这里重新打开，
    # 并给刻度数字留边距（否则 tight 裁切会把数字切掉）。
    ax.set_axis_on()
    fig.subplots_adjust(left=0.12, right=0.96, bottom=0.15, top=0.9)
    ax.tick_params(labelsize=8.5, length=3.2, width=0.8, pad=2)

    x0, x1 = spec.get("x", [-5, 5])
    y0, y1 = spec.get("y", [None, None])
    xs = np.linspace(float(x0), float(x1), int(spec.get("samples", 900)))

    funcs = spec.get("functions", [])
    ymin, ymax = np.inf, -np.inf
    samples: list[tuple[float, float]] = []
    for fn_spec in funcs:
        fn = make_fn(fn_spec["expr"])
        try:
            ys = np.asarray(fn(xs), dtype=float) * np.ones_like(xs)
        except ExprError:
            raise
        except Exception as e:  # noqa: BLE001
            raise ExprError(f"函数 {fn_spec['expr']} 计算失败：{e}") from e
        color = fn_spec.get("color", "#b3261e")
        lw = float(fn_spec.get("lw", 1.8))
        ls = fn_spec.get("style", "-")
        # 断开不连续点（tan、1/x 等）
        jump = (np.nanmax(ys) - np.nanmin(ys)) if np.isfinite(ys).any() else 1
        step = np.abs(np.diff(ys))
        cut = np.where(step > max(1.2, jump * 0.35))[0]
        start = 0
        seg_id = 0
        for cut_i in list(cut) + [len(xs) - 1]:
            seg_x, seg_y = xs[start:cut_i + 1], ys[start:cut_i + 1]
            good = np.isfinite(seg_y)
            if good.sum() > 1:
                ax.plot(seg_x[good], seg_y[good], color=color, lw=lw, ls=ls,
                        label=fn_spec.get("label") if seg_id == 0 else None)
                keep = np.where(good)[0][::3]
                samples.extend((float(seg_x[k]), float(seg_y[k])) for k in keep)
            start = cut_i + 1
            seg_id += 1
        if np.isfinite(ys).any():
            ymin = min(ymin, float(np.nanpercentile(ys[np.isfinite(ys)], 0.5)))
            ymax = max(ymax, float(np.nanpercentile(ys[np.isfinite(ys)], 99.5)))

    cross = spec.get("axes", "cross") == "cross"
    if cross:
        ax.spines["left"].set_position("zero")
        ax.spines["bottom"].set_position("zero")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["bottom"].set_linewidth(1.0)

    if spec.get("grid", True):
        ax.grid(True, linestyle=":", linewidth=0.6, color="#cfcfcf", zorder=0)
    ax.axhline(0, color=INK, lw=1.0, zorder=1)
    ax.axvline(0, color=INK, lw=1.0, zorder=1)
    ax.set_axisbelow(True)

    for a in spec.get("asymptotes", []):
        if "x" in a:
            ax.axvline(float(a["x"]), color=GREY, lw=1.0, ls=(0, (5, 4)))
        if "y" in a:
            ax.axhline(float(a["y"]), color=GREY, lw=1.0, ls=(0, (5, 4)))

    pts = spec.get("points", [])
    for p in pts:
        ax.plot(float(p["x"]), float(p["y"]), marker="o", ms=5, color=p.get("color", INK), zorder=5)
        if p.get("label"):
            dx, dy = p.get("offset", p.get("label_offset", [0.18, 0.22]))
            label(ax, float(p["x"]) + dx, float(p["y"]) + dy, p["label"], size=10, ha="left")
        if p.get("guides"):
            ax.plot([float(p["x"])] * 2, [0, float(p["y"])], color=GREY, lw=0.8, ls=":")
            ax.plot([0, float(p["x"])], [float(p["y"])] * 2, color=GREY, lw=0.8, ls=":")

    # ---- 值域：给了就用给的，没给就按函数值自动算（带 10% 余量）----
    if y0 is not None and y1 is not None:
        ax.set_ylim(float(y0), float(y1))
    elif np.isfinite(ymin) and np.isfinite(ymax):
        pad = max(0.1 * (ymax - ymin), 0.4)
        ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_xlim(float(x0), float(x1))

    # ---- 刻度 ----
    if spec.get("ticks", True):
        ax.tick_params(labelbottom=True, labelleft=True, bottom=True, left=True)
    else:
        ax.tick_params(labelbottom=False, labelleft=False, bottom=False, left=False)
    if spec.get("xstep"):
        ax.xaxis.set_major_locator(MultipleLocator(float(spec["xstep"])))
    if spec.get("ystep"):
        ax.yaxis.set_major_locator(MultipleLocator(float(spec["ystep"])))

    # ---- 轴名（放在坐标轴末端）----
    xl, yl = ax.get_xlim(), ax.get_ylim()
    ax_y = 0.0 if yl[0] <= 0 <= yl[1] else yl[0]
    ax_x = 0.0 if xl[0] <= 0 <= xl[1] else xl[0]
    label(ax, xl[1], ax_y, "$x$", ha="left", va="center", size=11)
    label(ax, ax_x, yl[1], "$y$", ha="center", va="bottom", size=11)

    # ---- 图例：auto 会挑一个曲线不经过的角 ----
    pos = spec.get("legend", spec.get("legend_loc", "auto"))
    if any(f.get("label") for f in funcs) and pos != "none":
        loc = _pick_legend(ax, samples, pts) if pos in ("auto", "best") else pos
        ax.legend(fontsize=9, frameon=False, loc=loc)

    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=11)
    return fig


def geometry(spec: dict):
    pts = {k: np.asarray(v, dtype=float) for k, v in spec["points"].items()}
    fig, ax = new_figure(*spec.get("size", [4.6, 4.0]))
    centroid = np.mean(list(pts.values()), axis=0) if pts else np.zeros(2)

    for seg in spec.get("segments", []):
        a, b = pts[seg[0]], pts[seg[1]]
        ax.plot([a[0], b[0]], [a[1], b[1]], color=seg[2] if len(seg) > 2 else INK,
                lw=1.5 if len(seg) <= 3 else seg[3] if len(seg) > 3 else 1.5)

    for pg in spec.get("polygons", []):
        poly(ax, [pts[n] for n in pg], fc=LIGHT, ec=INK, lw=1.5)

    for c in spec.get("circles", []):
        center = pts[c["center"]] if isinstance(c["center"], str) else np.asarray(c["center"])
        ax.add_patch(Circle(center, float(c["r"]), fill=False, edgecolor=INK, lw=1.5))
        if c.get("label"):
            label(ax, center[0], center[1], c["label"], size=10)

    for name, p in pts.items():
        ax.plot(*p, marker="o", ms=3.6, color=INK, zorder=6)
        if spec.get("labels", True):
            d = p - centroid
            nrm = np.linalg.norm(d)
            d = d / nrm if nrm > 1e-9 else np.array([0.0, 1.0])
            label(ax, *(p + d * 0.16), name, size=11, color=INK)

    for a, b, c in spec.get("right_angles", []):
        pb, u1, u2 = pts[b], None, None
        _, _, u1, _, _ = unit(pb, pts[a])
        _, _, u2, _, _ = unit(pb, pts[c])
        s = float(spec.get("right_angle_size", 0.18))
        poly(ax, [pb + u1 * s, pb + u1 * s + u2 * s, pb + u2 * s],
             fc="none", ec=INK, lw=1.0)

    for ang in spec.get("angles", []):
        p = pts[ang["at"]]
        _, _, u1, _, _ = unit(p, pts[ang["from"]])
        _, _, u2, _, _ = unit(p, pts[ang["to"]])
        a1 = np.degrees(np.arctan2(u1[1], u1[0]))
        a2 = np.degrees(np.arctan2(u2[1], u2[0]))
        diff = (a2 - a1 + 180) % 360 - 180
        if diff < 0:
            a1, a2 = a2, a1
            diff = -diff
        r = float(ang.get("r", 0.55))
        ax.add_patch(Arc(p, 2 * r, 2 * r, theta1=a1, theta2=a1 + diff, color=INK, lw=1.1))
        mid = np.deg2rad(a1 + diff / 2)
        label(ax, p[0] + (r + 0.3) * np.cos(mid), p[1] + (r + 0.3) * np.sin(mid),
              ang.get("label", ""), size=10, bg=True)

    for tick in spec.get("ticks", []):
        a, b = pts[tick["from"]], pts[tick["to"]]
        _, _, u, n, L = unit(a, b)
        mid = (a + b) / 2
        count = int(tick.get("n", 1))
        gap = float(tick.get("gap", 0.12))
        for k in range(count):
            off = (k - (count - 1) / 2) * gap
            p0 = mid + u * off + n * 0.09
            p1 = mid + u * off - n * 0.09
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=INK, lw=1.2)

    if spec.get("axes"):
        ax.axhline(0, color=INK, lw=0.9)
        ax.axvline(0, color=INK, lw=0.9)

    ax.margins(0.12)
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=11)
    return fig


def numberline(spec: dict):
    lo, hi = float(spec.get("min", -3)), float(spec.get("max", 5))
    fig, ax = new_figure(*spec.get("size", [6.4, 1.5]))
    ax.annotate("", xy=(hi + 0.5, 0), xytext=(lo - 0.5, 0),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.3, mutation_scale=12))
    step = spec.get("step", 1)
    x = np.arange(np.ceil(lo), np.floor(hi) + 1e-9, step)
    for v in x:
        ax.plot([v, v], [-0.09, 0.09], color=INK, lw=1.2)
        label(ax, v, -0.3, spec.get("tick_format", "").format(v) if spec.get("tick_format") else f"{v:g}",
              size=10)

    for p in spec.get("points", []):
        v = float(p["x"])
        filled = p.get("filled", True)
        ax.plot(v, 0, marker="o", ms=7, color=p.get("color", INK),
                mfc=p.get("color", INK) if filled else "white", mew=1.6, zorder=5)
        if p.get("label"):
            label(ax, v, 0.28, p["label"], size=10)

    for iv in spec.get("intervals", []):
        a, b = float(iv["from"]), float(iv["to"])
        y = 0.32
        ax.plot([a, b], [y, y], color=iv.get("color", "#2f5f9e"), lw=2.2)
        for endpoint, closed in ((a, iv.get("left_closed", True)), (b, iv.get("right_closed", True))):
            ax.plot(endpoint, y, marker="o", ms=5, color=iv.get("color", "#2f5f9e"),
                    mfc=iv.get("color", "#2f5f9e") if closed else "white", mew=1.4, zorder=6)
        if iv.get("label"):
            label(ax, (a + b) / 2, y + 0.26, iv["label"], size=9, color=iv.get("color", "#2f5f9e"))

    ax.set_xlim(lo - 0.7, hi + 0.7)
    ax.set_ylim(-0.65, 0.85)
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=11)
    return fig


def venn(spec: dict):
    sets = spec.get("sets", [{"label": "A"}, {"label": "B"}])
    fig, ax = new_figure(*spec.get("size", [4.6, 3.6]))
    r = float(spec.get("radius", 1.0))
    n = len(sets)
    if n == 1:
        pos = [(0, 0)]
    elif n == 2:
        pos = [(-0.55, 0), (0.55, 0)]
    else:
        pos = [(-0.6, -0.35), (0.6, -0.35), (0, 0.6)]

    ax.add_patch(Rectangle((-2.3, -1.6), 4.6, 3.2, fill=False, ec=GREY, lw=1.0))
    label(ax, -2.15, 1.4, spec.get("universe", "U"), size=11, color=GREY)

    for (x, y), s in zip(pos, sets):
        color = s.get("color", "#2f5f9e")
        ax.add_patch(Circle((x, y), r, facecolor=color, alpha=0.16, edgecolor=color, lw=1.6))
        lx = x + (r + 0.2) * (1 if x >= 0 else -1)
        label(ax, lx if n < 3 or s is not sets[2] else x, y + (r + 0.2 if n == 3 and s is sets[2] else 0),
              s.get("label", ""), size=12)

    counts = spec.get("counts", {})
    if n == 2:
        centers = {sets[0].get("label", "A") + "only": (-1.15, 0),
                   sets[1].get("label", "B") + "only": (1.15, 0),
                   "AB": (0, 0)}
    else:
        centers = {sets[0].get("label", "A") + "only": (-1.15, -0.45),
                   sets[1].get("label", "B") + "only": (1.15, -0.45),
                   sets[2].get("label", "C") + "only": (0, 1.05),
                   "AB": (0, -0.75), "AC": (-0.55, 0.35), "BC": (0.55, 0.35),
                   "ABC": (0, -0.2)}
    for key, value in counts.items():
        if key in centers:
            label(ax, *centers[key], str(value), size=11)

    ax.set_xlim(-2.5, 2.5)
    ax.set_ylim(-1.8, 1.9)
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=11)
    return fig
