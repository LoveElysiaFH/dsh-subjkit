# -*- coding: utf-8 -*-
"""生物图示：细胞结构示意图、过程流程框图。"""
from __future__ import annotations

import numpy as np
from matplotlib.patches import Circle, Ellipse, FancyBboxPatch, Polygon, Rectangle

from .base import BLUE, GREEN, GREY, INK, LIGHT, RED, arrow, label, new_figure

MEMBRANE = "#5b7fa6"
CYTO = "#fdf6e3"
NUCLEUS = "#e8c9d8"
VACUOLE = "#dcebf7"
CHLORO = "#cfe6c4"
MITO = "#f6d6b8"


def _leader(ax, text, target, at, color=INK):
    ax.annotate(text, xy=tuple(target), xytext=tuple(at), fontsize=9.5, color=color,
                ha="left" if at[0] >= target[0] else "right", va="center",
                arrowprops=dict(arrowstyle="-", color=GREY, lw=0.8,
                                connectionstyle="arc3,rad=0.12"), zorder=8)


# 内置标签：(文字, 箭头指向, 文字位置)。这里单独列出来，是因为
# ① `show_builtin_labels: false` 要能整组关掉；
# ② `--dry-run` 要把这些坐标报给使用者，让他们挑空位加自定义标注；
# ③ 自定义标注要跟它们做避让。
CELL_LABELS = {
    "plant": [
        ("细胞壁", (2.30, 1.20), (2.55, 1.55)),
        ("叶绿体", (1.45, 0.85), (2.55, 1.02)),
        ("细胞膜", (2.18, 0.55), (2.55, 0.55)),
        ("线粒体", (1.15, 0.15), (2.55, 0.05)),
        ("细胞核", (-1.45, 0.35), (-2.55, 0.85)),
        ("细胞质基质", (-0.20, -1.25), (0.90, -1.85)),
    ],
    "animal": [
        ("细胞膜", (2.10, 0.70), (2.45, 1.15)),
        ("线粒体", (1.00, 0.55), (2.50, 0.55)),
        ("高尔基体", (1.35, -0.87), (2.20, -1.50)),
        ("细胞核", (-0.75, 0.30), (-2.60, 1.00)),
        ("核糖体/内质网", (-1.45, -0.55), (-2.60, -1.20)),
    ],
}

# 自定义标注与已有标签的最小间距（数据坐标）
_GAP_X, _GAP_Y = 0.62, 0.20


def _occupied(at, occupied) -> bool:
    return any(abs(at[0] - ox) < _GAP_X and abs(at[1] - oy) < _GAP_Y for ox, oy in occupied)


def _place(at, occupied):
    """给自定义标注找一个不和别人重叠的位置：先往上挪，再往下挪。"""
    x, y = float(at[0]), float(at[1])
    if not _occupied((x, y), occupied):
        return [x, y]
    for step in (0.34, -0.34, 0.68, -0.68, 1.02, -1.02):
        cand = (x, y + step)
        if not _occupied(cand, occupied):
            return [x, round(cand[1], 3)]
    return [x, y]


def cell(spec: dict):
    kind = spec.get("kind", "plant")
    fig, ax = new_figure(*spec.get("size", [5.6, 4.2]))

    if kind == "plant":
        ax.add_patch(FancyBboxPatch((-2.3, -1.5), 4.6, 3.0, boxstyle="round,pad=0.02,rounding_size=0.18",
                                    facecolor="#f3f7ea", edgecolor="#6b8e4e", lw=2.4, zorder=1))
        ax.add_patch(FancyBboxPatch((-2.18, -1.38), 4.36, 2.76, boxstyle="round,pad=0.02,rounding_size=0.16",
                                    facecolor=CYTO, edgecolor=MEMBRANE, lw=1.4, zorder=2))
        ax.add_patch(Ellipse((0.25, 0.05), 2.5, 1.75, facecolor=VACUOLE, edgecolor=MEMBRANE, lw=1.2, zorder=3))
        label(ax, 0.25, 0.05, "液泡", size=10, color="#3b5b7a")

        ax.add_patch(Circle((-1.45, 0.35), 0.46, facecolor=NUCLEUS, edgecolor="#9c5b78", lw=1.3, zorder=4))
        ax.add_patch(Circle((-1.45, 0.35), 0.14, facecolor="#9c5b78", edgecolor="none", zorder=5))

        for cx, cy, ang in [(-1.55, -0.85, 20), (1.45, 0.85, -15), (1.55, -0.6, 35), (-0.55, 1.05, 5)]:
            ax.add_patch(Ellipse((cx, cy), 0.52, 0.26, angle=ang, facecolor=CHLORO,
                                 edgecolor="#4f7a3a", lw=1.1, zorder=4))

        for cx, cy, ang in [(-0.55, -1.0, -25), (1.15, 0.15, 60)]:
            ax.add_patch(Ellipse((cx, cy), 0.5, 0.24, angle=ang, facecolor=MITO,
                                 edgecolor="#a86a3a", lw=1.1, zorder=4))
    else:
        ax.add_patch(Ellipse((0, 0), 4.4, 3.0, facecolor=CYTO, edgecolor=MEMBRANE, lw=2.0, zorder=1))
        ax.add_patch(Circle((-0.75, 0.3), 0.55, facecolor=NUCLEUS, edgecolor="#9c5b78", lw=1.3, zorder=3))
        ax.add_patch(Circle((-0.75, 0.3), 0.16, facecolor="#9c5b78", edgecolor="none", zorder=4))
        for cx, cy, ang in [(1.0, 0.55, 25), (0.85, -0.55, -30), (-0.2, -0.9, 70)]:
            ax.add_patch(Ellipse((cx, cy), 0.55, 0.24, angle=ang, facecolor=MITO,
                                 edgecolor="#a86a3a", lw=1.1, zorder=3))
        for cx, cy, ang in [(-1.5, -0.55, -20), (-1.45, 0.9, 25)]:
            ax.add_patch(Ellipse((cx, cy), 0.5, 0.2, angle=ang, facecolor="#e2e2e2",
                                 edgecolor="#888", lw=0.9, zorder=2))
        # 高尔基体
        for k in range(3):
            ax.add_patch(Ellipse((1.35, -1.0 + k * 0.13), 0.5 - k * 0.06, 0.1,
                                 fill=False, edgecolor="#7a7a7a", lw=1.0, zorder=3))

    # 内置标签：可整组关掉（show_builtin_labels: false），
    # 开着的时候它们的位置会占位，自定义标注自动避开。
    labels = CELL_LABELS.get(kind, CELL_LABELS["plant"])
    occupied: list[tuple[float, float]] = []
    if spec.get("show_builtin_labels", True):
        for text, target, at in labels:
            _leader(ax, text, target, at)
            occupied.append((float(at[0]), float(at[1])))

    for note in spec.get("notes", []):
        at = _place(note["at"], occupied)
        occupied.append((at[0], at[1]))
        _leader(ax, note["text"], note["target"], at)

    ax.set_xlim(-3.3, 3.3)
    ax.set_ylim(-2.2, 2.0)
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=11)
    return fig


def flow(spec: dict):
    steps = spec.get("steps", [])
    if not steps:
        raise ValueError("flow 至少需要一个步骤")
    vertical = spec.get("layout", "horizontal") == "vertical"
    fig, ax = new_figure(*spec.get("size", [6.2, 1.6] if not vertical else [2.8, 5.2]))

    n = len(steps)
    box_w = float(spec.get("box_width", 1.55))
    box_h = float(spec.get("box_height", 0.62))
    gap = float(spec.get("gap", 0.55))

    centers = []
    for i in range(n):
        if vertical:
            centers.append((0, -i * (box_h + gap)))
        else:
            centers.append((i * (box_w + gap), 0))

    for i, step in enumerate(steps):
        text = step["text"] if isinstance(step, dict) else str(step)
        color = step.get("color", "#eef3fb") if isinstance(step, dict) else "#eef3fb"
        cx, cy = centers[i]
        ax.add_patch(FancyBboxPatch((cx - box_w / 2, cy - box_h / 2), box_w, box_h,
                                    boxstyle="round,pad=0.02,rounding_size=0.1",
                                    facecolor=color, edgecolor=INK, lw=1.2, zorder=2))
        label(ax, cx, cy, text, size=10.5, zorder=3)

    for i in range(n - 1):
        a, b = np.array(centers[i]), np.array(centers[i + 1])
        half = box_h / 2 if vertical else box_w / 2
        d = (b - a) / np.linalg.norm(b - a)
        arrow(ax, a + d * half, b - d * half, lw=1.4, ms=11)
        if isinstance(steps[i], dict) and steps[i].get("arrow_label"):
            mid = (a + b) / 2
            label(ax, mid[0] + (0.18 if not vertical else 0), mid[1] + (0 if not vertical else 0),
                  steps[i]["arrow_label"], size=8.5, color=GREY)

    ax.margins(0.12)
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=11)
    return fig
