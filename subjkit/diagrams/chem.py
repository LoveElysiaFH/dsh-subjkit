# -*- coding: utf-8 -*-
"""化学图示：常用仪器装置与分子结构式（SMILES）。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from matplotlib.patches import Circle, Ellipse, Polygon, Rectangle, Wedge

from .base import GREY, INK, LIGHT, label, new_figure, poly

WATER = "#dcebf7"
GLASS = "#33475b"


def _transform(ax, x, y, s, draw):
    def T(px, py):
        return (x + px * s, y + py * s)
    draw(T, s)


def _beaker(ax, x, y, s, water):
    T = lambda px, py: (x + px * s, y + py * s)
    pts = [T(-0.5, 1.2), T(-0.5, 0.05), T(-0.42, 0), T(0.42, 0), T(0.5, 0.05), T(0.5, 1.2)]
    if water:
        ax.add_patch(Polygon([T(-0.46, 0.08), T(-0.46, 0.55), T(0.46, 0.55), T(0.46, 0.08)],
                             closed=True, facecolor=WATER, edgecolor="none", zorder=2))
    ax.plot(*zip(*pts), color=GLASS, lw=1.7, zorder=3)
    ax.plot(*zip(T(-0.56, 1.22), T(-0.5, 1.2)), color=GLASS, lw=1.7)
    ax.plot(*zip(T(0.56, 1.22), T(0.5, 1.2)), color=GLASS, lw=1.7)


def _flask(ax, x, y, s, water):
    T = lambda px, py: (x + px * s, y + py * s)
    body = [T(-0.14, 1.15), T(-0.14, 0.55), T(-0.55, 0.02), T(0.55, 0.02), T(0.14, 0.55), T(0.14, 1.15)]
    if water:
        ax.add_patch(Polygon([T(-0.2, 0.08), T(-0.34, 0.3), T(0.34, 0.3), T(0.2, 0.08)],
                             closed=True, facecolor=WATER, edgecolor="none", zorder=2))
    ax.plot(*zip(*body), color=GLASS, lw=1.7, zorder=3)
    ax.plot(*zip(T(-0.2, 1.15), T(0.2, 1.15)), color=GLASS, lw=1.7)


def _round_flask(ax, x, y, s, water):
    T = lambda px, py: (x + px * s, y + py * s)
    r = 0.42
    ax.add_patch(Circle(T(0, 0.45), r * s, fill=False, edgecolor=GLASS, lw=1.7, zorder=3))
    if water:
        ax.add_patch(Wedge(T(0, 0.45), (r - 0.04) * s, 180, 360,
                           facecolor=WATER, edgecolor="none", zorder=2))
    ax.plot(*zip(T(-0.14, 0.86), T(-0.14, 1.25), T(0.14, 1.25), T(0.14, 0.86)), color=GLASS, lw=1.7)


def _test_tube(ax, x, y, s, water):
    T = lambda px, py: (x + px * s, y + py * s)
    ax.plot(*zip(T(-0.16, 1.15), T(-0.16, 0.14)), color=GLASS, lw=1.7)
    ax.plot(*zip(T(0.16, 1.15), T(0.16, 0.14)), color=GLASS, lw=1.7)
    ax.add_patch(Ellipse(T(0, 0.14), 0.32 * s, 0.28 * s, facecolor="white",
                         edgecolor=GLASS, lw=1.7, zorder=3))
    if water:
        ax.add_patch(Rectangle(T(-0.14, 0.15), 0.28 * s, 0.38 * s, facecolor=WATER,
                               edgecolor="none", zorder=2))
    ax.plot(*zip(T(-0.16, 1.15), T(0.16, 1.15)), color=GLASS, lw=1.7)


def _gas_jar(ax, x, y, s, water):
    T = lambda px, py: (x + px * s, y + py * s)
    ax.plot(*zip(T(-0.4, 1.15), T(-0.4, 0), T(0.4, 0), T(0.4, 1.15)), color=GLASS, lw=1.7)
    ax.plot(*zip(T(-0.44, 1.15), T(0.44, 1.15)), color=GLASS, lw=1.7)
    if water:
        ax.add_patch(Rectangle(T(-0.36, 0.04), 0.72 * s, 0.4 * s, facecolor=WATER,
                               edgecolor="none", zorder=2))


def _trough(ax, x, y, s, water):
    T = lambda px, py: (x + px * s, y + py * s)
    ax.plot(*zip(T(-0.9, 0.55), T(-0.9, 0), T(0.9, 0), T(0.9, 0.55)), color=GLASS, lw=1.7)
    ax.add_patch(Rectangle(T(-0.86, 0.05), 1.72 * s, 0.32 * s, facecolor=WATER,
                           edgecolor="none", zorder=2))


def _funnel(ax, x, y, s, water):
    T = lambda px, py: (x + px * s, y + py * s)
    ax.plot(*zip(T(-0.5, 1.0), T(-0.07, 0.45), T(-0.07, 0.1), T(0.07, 0.1), T(0.07, 0.45), T(0.5, 1.0)),
            color=GLASS, lw=1.7)
    ax.plot(*zip(T(-0.55, 1.0), T(0.55, 1.0)), color=GLASS, lw=1.7)


def _lamp(ax, x, y, s, water):
    T = lambda px, py: (x + px * s, y + py * s)
    ax.add_patch(Polygon([T(-0.3, 0), T(0.3, 0), T(0.2, 0.5), T(-0.2, 0.5)],
                         closed=True, facecolor="#f2d9a0", edgecolor=GLASS, lw=1.5, zorder=3))
    ax.plot(*zip(T(-0.22, 0.5), T(0.22, 0.5)), color=GLASS, lw=1.5)
    ax.plot(*zip(T(0, 0.5), T(0, 0.62)), color=INK, lw=1.6)
    flame = [T(0, 0.62), T(0.07, 0.74), T(0.02, 0.9), T(0, 0.98), T(-0.02, 0.9), T(-0.07, 0.74)]
    ax.add_patch(Polygon(flame, closed=True, facecolor="#f4a261", edgecolor="none", alpha=0.9, zorder=4))


def _stand(ax, x, y, s, water):
    T = lambda px, py: (x + px * s, y + py * s)
    ax.add_patch(Rectangle(T(-0.8, 0), 1.6 * s, 0.08 * s, facecolor="#555", edgecolor="none", zorder=3))
    ax.plot(*zip(T(-0.6, 0.08), T(-0.6, 1.9)), color="#555", lw=4.0, solid_capstyle="butt", zorder=4)
    ax.plot(*zip(T(-0.6, 1.35), T(0.1, 1.35)), color="#555", lw=2.4, zorder=4)


def _condenser(ax, x, y, s, water):
    T = lambda px, py: (x + px * s, y + py * s)
    ax.add_patch(Rectangle(T(-0.18, 0.15), 0.36 * s, 1.3 * s, facecolor="white",
                           edgecolor=GLASS, lw=1.7, zorder=3))
    ax.plot(*zip(T(0, 0.15), T(0, 1.45)), color=GLASS, lw=1.2, zorder=4)
    ax.plot(*zip(T(0.18, 1.15), T(0.3, 1.15)), color=GLASS, lw=1.7)
    ax.plot(*zip(T(-0.18, 0.4), T(-0.3, 0.4)), color=GLASS, lw=1.7)


def _thermometer(ax, x, y, s, water):
    T = lambda px, py: (x + px * s, y + py * s)
    ax.plot(*zip(T(-0.05, 1.45), T(-0.05, 0.18)), color=GLASS, lw=1.5)
    ax.plot(*zip(T(0.05, 1.45), T(0.05, 0.18)), color=GLASS, lw=1.5)
    ax.add_patch(Circle(T(0, 0.12), 0.12 * s, facecolor="#c0392b", edgecolor=GLASS, lw=1.2, zorder=4))
    ax.plot(*zip(T(0, 0.2), T(0, 0.85)), color="#c0392b", lw=2.0, zorder=4)


PARTS = {
    "beaker": _beaker, "flask": _flask, "round_flask": _round_flask,
    "test_tube": _test_tube, "gas_jar": _gas_jar, "trough": _trough,
    "funnel": _funnel, "alcohol_lamp": _lamp, "iron_stand": _stand,
    "condenser": _condenser, "thermometer": _thermometer,
}


def apparatus(spec: dict):
    fig, ax = new_figure(*spec.get("size", [4.8, 4.0]))
    for part in spec.get("parts", []):
        kind = part["kind"]
        x, y = part.get("at", [0, 0])
        s = float(part.get("scale", 1.0))
        if kind == "tube":
            pts = np.asarray(part.get("points", []), dtype=float)
            if len(pts) >= 2:
                ax.plot(pts[:, 0], pts[:, 1], color=GLASS, lw=1.7, solid_joinstyle="round")
            continue
        fn = PARTS.get(kind)
        if fn is None:
            raise ValueError(f"不认识的仪器：{kind}（可用：{', '.join(PARTS)}）")
        fn(ax, x, y, s, part.get("water", True))

    for item in spec.get("labels", []):
        label(ax, *item["at"], item.get("text", ""), size=item.get("size", 10),
              ha=item.get("ha", "center"), va=item.get("va", "center"))
    for item in spec.get("notes", []):
        ax.annotate(item["text"], xy=tuple(item["target"]), xytext=tuple(item["at"]),
                    fontsize=10, ha=item.get("ha", "left"), va="center",
                    arrowprops=dict(arrowstyle="-", color=GREY, lw=0.9,
                                    connectionstyle="arc3,rad=0.15"))

    ax.margins(0.12)
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=11)
    return fig


def molecule(spec: dict, out: str | Path) -> Path:
    from rdkit import Chem
    from rdkit.Chem.Draw import rdMolDraw2D

    smiles = spec["smiles"]
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"SMILES 无法解析：{smiles}")
    w, h = spec.get("pixels", [900, 650])
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".png":
        drawer = rdMolDraw2D.MolDraw2DCairo(int(w), int(h))
        opts = drawer.drawOptions()
        opts.addStereoAnnotation = True
        opts.bondLineWidth = 2
        opts.padding = 0.08
        opts.backgroundColour = (1, 1, 1, 1)
        drawer.DrawMolecule(mol, legend=spec.get("label", ""))
        drawer.FinishDrawing()
        out.write_bytes(drawer.GetDrawingText())
    else:
        drawer = rdMolDraw2D.MolDraw2DSVG(int(w), int(h))
        opts = drawer.drawOptions()
        opts.addStereoAnnotation = True
        opts.bondLineWidth = 2
        opts.padding = 0.08
        opts.backgroundColour = (1, 1, 1, 1)
        drawer.DrawMolecule(mol, legend=spec.get("label", ""))
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()
        svg = svg.replace("<?xml version='1.0' encoding='iso-8859-1'?>", "")
        out.write_text(svg, encoding="utf-8")
    return out
