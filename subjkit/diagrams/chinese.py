# -*- coding: utf-8 -*-
"""语文图示：田字格 / 米字格练字纸（带拼音）。"""
from __future__ import annotations

import math

from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle

from .base import GREY, INK, label, new_figure


def grid(spec: dict):
    chars = spec.get("chars", "")
    if not chars:
        raise ValueError("grid 需要 chars（要练的字）")
    pinyin = spec.get("pinyin") or []
    cols = int(spec.get("cols", 5))
    rows = math.ceil(len(chars) / cols)
    style = spec.get("style", "tian")
    cell = 1.0
    gap = float(spec.get("gap", 0.12))
    with_pinyin = bool(pinyin)

    width = cols * (cell + gap) + gap
    top = 0.55 if with_pinyin else 0.35
    height = rows * (cell + gap) + gap + top + 0.3
    fig, ax = new_figure(width * 0.72, height * 0.72)

    font_char = FontProperties(family=spec.get("font", "KaiTi"), size=spec.get("char_size", 34))
    font_py = FontProperties(family="Times New Roman", size=9)

    for i, ch in enumerate(chars):
        r, c = divmod(i, cols)
        x = gap + c * (cell + gap)
        y = height - top - (r + 1) * (cell + gap)
        ax.add_patch(Rectangle((x, y), cell, cell, fill=False, ec=INK, lw=1.0, zorder=2))
        dash = dict(color="#9a9a9a", lw=0.7, ls=(0, (3, 3)), zorder=1)
        ax.plot([x, x + cell], [y + cell / 2] * 2, **dash)
        ax.plot([x + cell / 2] * 2, [y, y + cell], **dash)
        if style == "mi":
            ax.plot([x, x + cell], [y, y + cell], **dash)
            ax.plot([x, x + cell], [y + cell, y], **dash)
        ax.text(x + cell / 2, y + cell / 2 - 0.02, ch, ha="center", va="center",
                color=INK, fontproperties=font_char, zorder=3)
        if with_pinyin and i < len(pinyin) and pinyin[i]:
            ax.text(x + cell / 2, y + cell + 0.12, pinyin[i], ha="center", va="bottom",
                    color=GREY, fontproperties=font_py, zorder=3)

    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=11)
    return fig
