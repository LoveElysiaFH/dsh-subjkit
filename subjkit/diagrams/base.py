# -*- coding: utf-8 -*-
"""图示绘制基础：统一字体、画布、箭头与保存。所有图示最终是矢量图，可直接进 PDF。"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["SimSun", "Microsoft YaHei", "SimHei", "Noto Sans SC", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "mathtext.fontset": "cm",
    "mathtext.default": "it",
    "svg.fonttype": "path",          # 文字转路径：换机器、换字体也不会变形
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "font.size": 11,
    "lines.linewidth": 1.4,
    "lines.solid_capstyle": "round",
})

INK = "#111111"
BLUE = "#2f5f9e"
RED = "#b3261e"
GREEN = "#2e7d32"
GREY = "#777777"
LIGHT = "#e8eef7"


def new_figure(width: float = 6.0, height: float = 3.4, equal: bool = True):
    fig, ax = plt.subplots(figsize=(width, height))
    if equal:
        ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    return fig, ax


def finish(fig, out: str | Path, pad: float = 0.07, dpi: int = 300) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", pad_inches=pad, dpi=dpi, facecolor="white")
    plt.close(fig)
    return out


def arrow(ax, p, q, color=INK, lw=1.6, ms=13, ls="-", double=False, zorder=3, alpha=1.0):
    style = "<|-|>" if double else "-|>"
    ax.annotate(
        "", xy=tuple(q), xytext=tuple(p),
        arrowprops=dict(arrowstyle=style, color=color, lw=lw, mutation_scale=ms,
                        linestyle=ls, shrinkA=0, shrinkB=0, alpha=alpha),
        zorder=zorder,
    )


def label(ax, x, y, text, size=11, ha="center", va="center", color=INK,
          bg=False, rot=0, weight="normal", zorder=6, alpha=1.0):
    kw = {}
    if bg:
        kw["bbox"] = dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.92)
    ax.text(x, y, text, fontsize=size, ha=ha, va=va, color=color, rotation=rot,
            fontweight=weight, zorder=zorder, alpha=alpha, **kw)


def unit(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    v = b - a
    n = float(np.linalg.norm(v))
    if n == 0:
        return a, b, np.array([1.0, 0.0]), np.array([0.0, 1.0]), 0.0
    u = v / n
    return a, b, u, np.array([-u[1], u[0]]), n


def poly(ax, pts, fc="white", ec=INK, lw=1.4, zorder=2, alpha=1.0, closed=True, ls="-"):
    patch = Polygon(np.asarray(pts, dtype=float), closed=closed, facecolor=fc,
                    edgecolor=ec, linewidth=lw, zorder=zorder, alpha=alpha, linestyle=ls)
    ax.add_patch(patch)
    return patch


def hatched_ground(ax, x0, x1, y=0.0, color=INK, lw=1.4, tick=0.12):
    ax.plot([x0, x1], [y, y], color=color, lw=lw, zorder=2)
    for x in np.arange(x0, x1 + 1e-9, tick * 2.2):
        ax.plot([x, x - tick], [y, y - tick], color=color, lw=0.9, zorder=2)


def parabola_points(expr_fn, x0, x1, n=600):
    xs = np.linspace(x0, x1, n)
    ys = expr_fn(xs)
    ys = np.asarray(ys, dtype=float)
    if ys.shape != xs.shape:
        ys = np.broadcast_to(ys, xs.shape).astype(float)
    return xs, ys
