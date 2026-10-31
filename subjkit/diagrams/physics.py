# -*- coding: utf-8 -*-
"""物理图示：电路、受力、斜面、凸透镜光路。"""
from __future__ import annotations

import numpy as np
from matplotlib.patches import Arc, Circle, Rectangle

from .base import (BLUE, GREEN, GREY, INK, LIGHT, RED, arrow, finish, hatched_ground,
                   label, new_figure, poly, unit)

# ---------------------------------------------------------------- 电路

HALF = {
    "wire": 0.0, "battery": 0.10, "battery2": 0.22, "resistor": 0.36,
    "lamp": 0.21, "switch": 0.30, "ammeter": 0.24, "voltmeter": 0.24,
    "capacitor": 0.08, "rheostat": 0.36, "fuse": 0.26, "motor": 0.24,
}


def _element(ax, a, b, spec):
    kind = spec.get("kind", "wire")
    a, b, u, n, L = unit(a, b)
    c = (a + b) / 2
    half = HALF.get(kind, 0.0)
    lw = spec.get("lw", 1.5)
    color = spec.get("color", INK)

    if kind != "wire":
        ax.plot([a[0], (c - u * half)[0]], [a[1], (c - u * half)[1]], color=color, lw=lw, zorder=2)
        ax.plot([(c + u * half)[0], b[0]], [(c + u * half)[1], b[1]], color=color, lw=lw, zorder=2)

    def P(s, t):
        return c + u * s + n * t

    if kind == "wire":
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, zorder=2)
    elif kind == "battery":
        ax.plot(*zip(P(-0.05, 0.26), P(-0.05, -0.26)), color=color, lw=2.2, zorder=3)
        ax.plot(*zip(P(0.06, 0.13), P(0.06, -0.13)), color=color, lw=3.2, zorder=3)
    elif kind == "battery2":
        for s in (-0.16, 0.02):
            ax.plot(*zip(P(s - 0.05, 0.24), P(s - 0.05, -0.24)), color=color, lw=2.0, zorder=3)
            ax.plot(*zip(P(s + 0.06, 0.12), P(s + 0.06, -0.12)), color=color, lw=3.0, zorder=3)
    elif kind == "resistor":
        poly(ax, [P(-0.36, 0.15), P(0.36, 0.15), P(0.36, -0.15), P(-0.36, -0.15)],
             fc="white", ec=color, lw=lw, zorder=3)
    elif kind == "lamp":
        ax.add_patch(Circle(c, 0.21, facecolor="white", edgecolor=color, lw=lw, zorder=3))
        d = 0.21 / np.sqrt(2)
        ax.plot([c[0] - d, c[0] + d], [c[1] - d, c[1] + d], color=color, lw=1.2, zorder=4)
        ax.plot([c[0] - d, c[0] + d], [c[1] + d, c[1] - d], color=color, lw=1.2, zorder=4)
    elif kind == "switch":
        p1, p2 = P(-0.30, 0), P(0.30, 0)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, lw=0, zorder=2)
        ax.plot(*p1, marker="o", ms=3.2, color=color, zorder=4)
        ax.plot(*p2, marker="o", ms=3.2, color=color, zorder=4)
        ang = np.deg2rad(spec.get("angle", 32))
        tip = p1 + (u * np.cos(ang) + n * np.sin(ang)) * 0.56
        ax.plot([p1[0], tip[0]], [p1[1], tip[1]], color=color, lw=lw + 0.2, zorder=4)
    elif kind in ("ammeter", "voltmeter", "motor"):
        ax.add_patch(Circle(c, 0.24, facecolor="white", edgecolor=color, lw=lw, zorder=3))
        letter = {"ammeter": "A", "voltmeter": "V", "motor": "M"}[kind]
        label(ax, c[0], c[1] - 0.01, letter, size=11, color=color, zorder=4)
    elif kind == "capacitor":
        ax.plot(*zip(P(-0.05, 0.22), P(-0.05, -0.22)), color=color, lw=2.0, zorder=3)
        ax.plot(*zip(P(0.05, 0.22), P(0.05, -0.22)), color=color, lw=2.0, zorder=3)
    elif kind == "rheostat":
        poly(ax, [P(-0.36, 0.15), P(0.36, 0.15), P(0.36, -0.15), P(-0.36, -0.15)],
             fc="white", ec=color, lw=lw, zorder=3)
        arrow(ax, P(-0.28, 0.34), P(0.26, -0.30), color=color, lw=1.1, ms=8)
    elif kind == "fuse":
        poly(ax, [P(-0.26, 0.12), P(0.26, 0.12), P(0.26, -0.12), P(-0.26, -0.12)],
             fc="white", ec=color, lw=lw, zorder=3)
        ax.plot(*zip(P(-0.26, 0), P(0.26, 0)), color=color, lw=1.0, zorder=4)

    text = spec.get("label")
    if text:
        off = 0.44 if kind not in ("wire", "switch") else 0.34
        ln = n if n[0] > -1e-9 else -n
        pos = c + ln * off
        if abs(ln[0]) > 0.3:
            ha = "left" if ln[0] > 0 else "right"
            va = "center"
        else:
            ha = "center"
            va = "bottom" if ln[1] > 0 else "top"
        label(ax, pos[0], pos[1], text, size=10.5, ha=ha, va=va, bg=True, zorder=6)


def circuit(spec: dict):
    nodes = {k: np.asarray(v, dtype=float) for k, v in spec["nodes"].items()}
    fig, ax = new_figure(*spec.get("size", [5.8, 3.2]))
    degrees = {}
    for e in spec.get("elements", []):
        degrees[e["from"]] = degrees.get(e["from"], 0) + 1
        degrees[e["to"]] = degrees.get(e["to"], 0) + 1
        _element(ax, nodes[e["from"]], nodes[e["to"]], e)

    for name, d in degrees.items():
        if d >= 3:
            ax.plot(*nodes[name], marker="o", ms=4.2, color=INK, zorder=5)

    for item in spec.get("labels", []):
        label(ax, *item["at"], item.get("text", ""), size=item.get("size", 10.5),
              ha=item.get("ha", "center"), va=item.get("va", "center"))

    xs = [p[0] for p in nodes.values()]
    ys = [p[1] for p in nodes.values()]
    ax.set_xlim(min(xs) - 0.65, max(xs) + 0.65)
    ax.set_ylim(min(ys) - 0.55, max(ys) + 0.55)
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=11, pad=6)
    return fig


# ---------------------------------------------------------------- 受力图

def _body_shape(ax, center, body):
    w, h = body.get("w", 1.2), body.get("h", 0.75)
    shape = body.get("shape", "block")
    if shape == "circle":
        r = body.get("r", 0.55)
        ax.add_patch(Circle(center, r, facecolor=LIGHT, edgecolor=INK, lw=1.6, zorder=2))
        return r
    ax.add_patch(Rectangle((center[0] - w / 2, center[1] - h / 2), w, h,
                           facecolor=LIGHT, edgecolor=INK, lw=1.6, zorder=2))
    if body.get("label"):
        label(ax, center[0], center[1], body["label"], size=11, zorder=3)
    return None


def _edge_start(center, direction, body):
    if body.get("shape") == "circle":
        return center + direction * body.get("r", 0.55)
    w, h = body.get("w", 1.2) / 2, body.get("h", 0.75) / 2
    dx, dy = abs(direction[0]), abs(direction[1])
    tx = w / dx if dx > 1e-9 else np.inf
    ty = h / dy if dy > 1e-9 else np.inf
    return center + direction * min(tx, ty)


def force(spec: dict):
    body = spec.get("body", {})
    fig, ax = new_figure(*spec.get("size", [4.8, 3.6]))
    center = np.array(spec.get("center", [0.0, 0.0]), dtype=float)
    r = _body_shape(ax, center, body)

    forces = spec.get("forces", [])
    mags = [float(f.get("magnitude", 1.0)) for f in forces] or [1.0]
    scale = float(spec.get("scale", 1.55 / max(mags)))
    xs, ys = [center[0]], [center[1]]
    for f in forces:
        ang = np.deg2rad(float(f.get("angle", 0)))
        d = np.array([np.cos(ang), np.sin(ang)])
        start = center + d * (r if r else 0.0)
        if not r:
            start = _edge_start(center, d, body)
        length = float(f.get("magnitude", 1.0)) * scale
        tip = start + d * length
        color = f.get("color", INK)
        arrow(ax, start, tip, color=color, lw=f.get("lw", 1.8), ms=14)
        text = f.get("label", "")
        if text:
            lab = tip + d * 0.14
            label(ax, lab[0], lab[1], text, size=11, color=color, bg=True)
            xs.append(lab[0])
            ys.append(lab[1])
        xs.extend([start[0], tip[0]])
        ys.extend([start[1], tip[1]])

    if spec.get("ground"):
        y = center[1] - body.get("h", 0.75) / 2
        hatched_ground(ax, center[0] - 1.9, center[0] + 1.9, y)
        xs.extend([center[0] - 1.9, center[0] + 1.9])
        ys.append(y)

    for note in spec.get("notes", []):
        label(ax, *note["at"], note.get("text", ""), size=note.get("size", 10),
              ha=note.get("ha", "center"), color=note.get("color", GREY))
        xs.append(float(note["at"][0]))
        ys.append(float(note["at"][1]))

    pad_x = float(spec.get("pad_x", 0.35))
    pad_y = float(spec.get("pad_y", 0.3))
    ax.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
    ax.set_ylim(min(ys) - pad_y, max(ys) + pad_y)
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=11, pad=6)
    return fig


# ---------------------------------------------------------------- 斜面

def incline(spec: dict):
    theta = np.deg2rad(float(spec.get("angle", 30)))
    L = float(spec.get("length", 3.6))
    H = L * np.tan(theta)
    w, h = spec.get("block", [0.9, 0.55])[:2]
    fig, ax = new_figure(*spec.get("size", [5.0, 3.0]))

    poly(ax, [(0, 0), (L, 0), (L, H)], fc=LIGHT, ec=INK, lw=1.6)
    hatched_ground(ax, -0.7, L + 0.6, 0)
    label(ax, L * 0.32, -0.22, spec.get("base_label", ""), size=10, color=GREY)
    label(ax, L + 0.1, H * 0.5, spec.get("height_label", "h"), size=10, color=GREY, ha="left")

    u = np.array([np.cos(theta), np.sin(theta)])
    n = np.array([-np.sin(theta), np.cos(theta)])
    t = float(spec.get("position", 0.55))
    on_slope = np.array([t * L, t * H])
    center = on_slope + n * (h / 2)
    corners = []
    for sx, sy in [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]:
        corners.append(center + u * sx + n * sy)
    poly(ax, corners, fc="white", ec=INK, lw=1.6)
    if spec.get("block_label"):
        label(ax, center[0] + u[0] * 0.16, center[1] + u[1] * 0.16,
              spec["block_label"], size=11, bg=True)

    mag = float(spec.get("gravity", 1.15))
    forces = spec.get("forces", ["G", "N", "f"])
    g_tip = center + np.array([0, -mag])
    bottom = center - n * (h / 2)
    top = center + n * (h / 2)
    if "G" in forces:
        arrow(ax, bottom, g_tip, lw=1.8)
        label(ax, g_tip[0] - 0.08, g_tip[1], "$G$", ha="right", va="center")
    if "N" in forces:
        n_tip = top + n * (mag * 0.8)
        arrow(ax, top, n_tip, lw=1.8)
        label(ax, *(n_tip + n * 0.14), "$N$", bg=True)
    if "f" in forces:
        # 摩擦力画在接触面上，默认沿斜面向上（物块有下滑趋势）
        contact = on_slope + n * 0.03
        fdir = u if spec.get("friction_up", True) else -u
        f_tip = contact + fdir * (mag * 0.5)
        arrow(ax, contact, f_tip, color=RED, lw=1.8)
        label(ax, *(f_tip + n * 0.16), "$f$", color=RED, bg=True)

    if spec.get("decompose"):
        gpar = -u * (mag * np.sin(theta))
        gperp = -n * (mag * np.cos(theta))
        p_tip = center + gpar
        q_tip = center + gperp
        arrow(ax, center, p_tip, color=BLUE, lw=1.3, ls=(0, (5, 3)), ms=10)
        arrow(ax, center, q_tip, color=BLUE, lw=1.3, ls=(0, (5, 3)), ms=10)
        # 平行四边形辅助线：两个分力合成为 G
        ax.plot([p_tip[0], g_tip[0]], [p_tip[1], g_tip[1]], color=BLUE, lw=0.8, ls=(0, (2, 3)))
        ax.plot([q_tip[0], g_tip[0]], [q_tip[1], g_tip[1]], color=BLUE, lw=0.8, ls=(0, (2, 3)))
        label(ax, *(p_tip + n * 0.2), r"$mg\sin\theta$", color=BLUE, size=9.5, bg=True)
        label(ax, *(q_tip - u * 0.2), r"$mg\cos\theta$", color=BLUE, size=9.5, bg=True)

    arc = Arc((0, 0), 1.5, 1.5, theta1=0, theta2=np.rad2deg(theta), color=INK, lw=1.1)
    ax.add_patch(arc)
    label(ax, 0.62 * np.cos(theta / 2), 0.62 * np.sin(theta / 2), r"$\theta$", size=10)

    ax.set_xlim(-0.9, L + 1.0)
    ax.set_ylim(min(-0.7, center[1] - mag - 0.55), max(H + 0.55, center[1] + mag * 0.88 + 0.55))
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=11, pad=6)
    return fig


# ---------------------------------------------------------------- 凸透镜光路

def optics(spec: dict):
    f = float(spec.get("focal", 1.6))
    u = float(spec.get("object_distance", 2.8))
    h = float(spec.get("object_height", 1.0))
    fig, ax = new_figure(*spec.get("size", [6.2, 3.4]))
    H = 1.45

    ax.plot([-5.4, 5.4], [0, 0], color=INK, lw=1.0)
    ax.annotate("", xy=(5.5, 0), xytext=(5.35, 0), arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.0))

    # 双凸透镜：左右两段椭圆弧
    ax.add_patch(Arc((0, 0), 0.34, 2 * H, theta1=-90, theta2=90, color=INK, lw=1.8))
    ax.add_patch(Arc((0, 0), 0.34, 2 * H, theta1=90, theta2=270, color=INK, lw=1.8))

    for x, text in [(-f, "$F$"), (f, "$F'$"), (-2 * f, "$2F$"), (2 * f, "$2F'$")]:
        ax.plot([x, x], [-0.08, 0.08], color=INK, lw=1.2)
        label(ax, x, -0.26, text, size=10)
    label(ax, 0, -H - 0.28, "$O$", size=10)

    # 物
    ax.annotate("", xy=(-u, h), xytext=(-u, 0),
                arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.8, mutation_scale=12))
    label(ax, -u - 0.18, h * 0.6, "$AB$", color=BLUE, ha="right")
    label(ax, -u + 0.55, -0.32, "$u$", size=9, color=GREY)

    v = u * f / (u - f) if abs(u - f) > 1e-9 else 1e9
    hp = -h * v / u
    xmax = 5.0

    # 平行于主轴 → 过 F'
    ax.plot([-u, 0], [h, h], color=RED, lw=1.1)
    if v > 0:
        ax.plot([0, min(v, xmax)], [h, h * (f - min(v, xmax)) / f], color=RED, lw=1.1)
    else:
        ax.plot([0, xmax], [h, h * (f - xmax) / f], color=RED, lw=1.1)
        ax.plot([0, v], [h, h * (f - v) / f], color=RED, lw=1.0, ls=(0, (4, 3)))

    # 过光心
    ax.plot([-u, xmax], [h, -h * xmax / u], color=GREEN, lw=1.1)
    if v < 0:
        ax.plot([0, v], [0, -h * v / u], color=GREEN, lw=1.0, ls=(0, (4, 3)))

    # 过 F → 平行主轴
    y3 = -h * f / (u - f) if abs(u - f) > 1e-9 else 0
    ax.plot([-u, 0], [h, y3], color="#7b4fa0", lw=1.1)
    ax.plot([0, xmax], [y3, y3], color="#7b4fa0", lw=1.1)
    if v < 0:
        ax.plot([0, v], [y3, y3], color="#7b4fa0", lw=1.0, ls=(0, (4, 3)))

    if abs(v) < xmax:
        ax.plot([v, v], [0, hp], color=GREY, lw=0.9, ls=(0, (2, 2)))
        ax.annotate("", xy=(v, hp), xytext=(v, 0),
                    arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.6, mutation_scale=12))
        label(ax, v + 0.18, hp * 0.55, "$A'B'$" if v > 0 else "$A'B'$（虚像）",
              color=RED, ha="left" if v > 0 else "right")

    ax.set_xlim(-5.5, 5.5)
    ax.set_ylim(-H - 0.55, H + 0.55)
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=11, pad=4)
    return fig
