# -*- coding: utf-8 -*-
"""图示回归测试：一次渲染全部模板，检查文字/布局。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from subjkit.diagrams.figures import render  # noqa: E402

OUT = ROOT / "示例" / "输出" / "图示"
OUT.mkdir(parents=True, exist_ok=True)

SPECS = {
    "电路_串联": {
        "type": "circuit", "size": [5.8, 3.2],
        "nodes": {"A": [0, 0], "B": [5, 0], "C": [5, 2.6], "D": [0, 2.6]},
        "elements": [
            {"kind": "battery", "from": "A", "to": "B", "label": "$6\\,\\mathrm{V}$"},
            {"kind": "switch", "from": "B", "to": "C", "label": "$S$"},
            {"kind": "lamp", "from": "C", "to": "D", "label": "$L$"},
            {"kind": "resistor", "from": "D", "to": "A", "label": "$R=2\\,\\Omega$"},
        ],
    },
    "受力_水平面": {
        "type": "force", "size": [4.8, 3.6], "ground": True,
        "body": {"w": 1.2, "h": 0.7, "label": "$m$"},
        "forces": [
            {"label": "$G$", "angle": -90, "magnitude": 5},
            {"label": "$N$", "angle": 90, "magnitude": 5},
            {"label": "$F$", "angle": 0, "magnitude": 3},
            {"label": "$f$", "angle": 180, "magnitude": 2, "color": "#b3261e"},
        ],
    },
    "斜面_重力分解": {
        "type": "incline", "size": [5.2, 3.1], "angle": 30,
        "block_label": "$m$", "decompose": True, "base_label": "$L$",
    },
    "凸透镜成像": {
        "type": "optics", "size": [6.2, 3.4], "focal": 1.5,
        "object_distance": 2.8, "object_height": 1.0,
    },
    "函数图像": {
        "type": "plot", "size": [5.6, 3.7], "x": [-3, 4], "y": [-3, 7],
        "functions": [
            {"expr": "x^2-2*x", "label": "$y=x^2-2x$", "color": "#b3261e"},
            {"expr": "2*x-3", "label": "$y=2x-3$", "color": "#2f5f9e"},
        ],
        "points": [{"x": 1, "y": -1, "label": "$(1,-1)$"}],
        "asymptotes": [],
    },
    "平面几何": {
        "type": "geometry", "size": [4.4, 3.6],
        "points": {"A": [0, 0], "B": [4, 0], "C": [2, 3.4]},
        "segments": [["A", "B"], ["B", "C"], ["C", "A"]],
        "angles": [{"at": "A", "from": "B", "to": "C", "label": "$60^\\circ$", "r": 0.7}],
        "ticks": [{"from": "A", "to": "B", "n": 1}, {"from": "B", "to": "C", "n": 1}],
    },
    "数轴": {
        "type": "numberline", "size": [6.4, 1.4], "min": -2, "max": 5,
        "points": [{"x": -1, "filled": True, "label": "$-1$"}, {"x": 2, "filled": False, "label": "$2$"}],
        "intervals": [{"from": -1, "to": 2, "left_closed": True, "right_closed": False, "label": "$[-1,2)$"}],
    },
    "韦恩图": {
        "type": "venn", "size": [4.4, 3.4],
        "sets": [{"label": "A", "color": "#2f5f9e"}, {"label": "B", "color": "#2e7d32"}],
        "counts": {"Aonly": 6, "AB": 4, "Bonly": 7},
    },
    "化学装置": {
        "type": "apparatus", "size": [4.8, 4.2],
        "parts": [
            {"kind": "beaker", "at": [0, 0], "scale": 1.0},
            {"kind": "funnel", "at": [0.9, 1.05], "scale": 0.8},
            {"kind": "alcohol_lamp", "at": [-1.2, 0], "scale": 0.9},
        ],
        "labels": [{"text": "过滤装置", "at": [0.2, -0.2], "size": 10}],
    },
    "细胞_植物": {"type": "cell", "kind": "plant", "size": [5.6, 4.2]},
    "流程_光合作用": {
        "type": "flow", "size": [6.4, 1.5],
        "steps": ["光反应", "ATP、NADPH", "暗反应"],
    },
    "田字格": {
        "type": "grid", "chars": "春江花月夜", "pinyin": ["chūn", "jiāng", "huā", "yuè", "yè"],
        "cols": 5,
    },
    "分子_乙醇": {"type": "molecule", "smiles": "CCO", "label": "乙醇", "pixels": [700, 450]},
}


def main() -> int:
    failures = 0
    for name, spec in SPECS.items():
        out = OUT / f"{name}.svg"
        try:
            render(spec, out)
            print(f"✔ {name} → {out.name} ({out.stat().st_size // 1024} KB)")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"✘ {name}: {e}")
    (OUT / "specs.json").write_text(json.dumps(SPECS, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
