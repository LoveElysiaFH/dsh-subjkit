# -*- coding: utf-8 -*-
"""图示 spec 的校验与归一化：把「Python traceback」换成「人能照着改的一句话」。

设计原则：

1. **报错要说清哪里错、该怎么写**，并附一段能直接跑的最小 spec；
2. 能安全猜的写法就**自动修正并在结果里说一声**（`2x` → `2*x`、`["beaker"]` → 摆好位置的仪器），
   猜不动的（`xy` 是 x·y 还是变量名？`x2` 是 x² 还是 x·2？）就报错，绝不擅自改；
3. 归一化之后交给模板函数，模板里不再做参数猜测。

对外 `normalize(spec) -> (spec_out, warnings, info)`：
    · `spec_out` 已补好简写/别名，可直接交给模板；
    · `warnings` 是「我替你改了什么」；
    · `info` 给 `--dry-run` 用（模板、关键字段、cell 的内置标签坐标）。
"""
from __future__ import annotations

import json

from .bio import CELL_LABELS
from .chem import PARTS
from .expr import ExprError, compile_expr, normalize_expr

TEMPLATES = (
    "circuit", "force", "incline", "optics", "plot", "geometry", "numberline",
    "venn", "apparatus", "molecule", "cell", "flow", "grid",
)

LEGEND_POSITIONS = {
    "auto": "auto", "ur": "upper right", "ul": "upper left",
    "br": "lower right", "bl": "lower left", "none": "none",
    "upper right": "upper right", "upper left": "upper left",
    "lower right": "lower right", "lower left": "lower left",
    "best": "best",
}


class SpecError(ValueError):
    """spec 不合法。消息是给人看的中文，附最小可运行示例。"""

    def __init__(self, message: str, example: dict | None = None):
        self.message = message
        self.example = example
        super().__init__(message)

    def __str__(self) -> str:  # pragma: no cover - 只影响 CLI 输出
        if not self.example:
            return self.message
        return f"{self.message}\n  可用示例：{json.dumps(self.example, ensure_ascii=False)}"


# --------------------------------------------------------------------------
# 小工具
# --------------------------------------------------------------------------

def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _require(spec: dict, key: str, what: str, example: dict) -> None:
    if key not in spec or spec[key] is None:
        raise SpecError(f"缺少字段 {key}：{what}", example)


def _expect_list(spec: dict, key: str, what: str, example: dict) -> list:
    value = spec.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise SpecError(
            f"{key} 应为数组：{what}（实际传了 {type(value).__name__}"
            f"{'：' + str(value)[:40] if not isinstance(value, (dict,)) else ''}）",
            example,
        )
    return value


def _expect_pair(value, key: str, example: dict) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2 or not all(_is_num(v) for v in value):
        raise SpecError(f"{key} 应为 [x, y] 两个数字，例如 [1.5, 0.3]", example)
    return [float(value[0]), float(value[1])]


# --------------------------------------------------------------------------
# plot
# --------------------------------------------------------------------------

PLOT_EXAMPLE = {
    "type": "plot",
    "x": [-3, 4],
    "functions": [{"expr": "x**2-2*x", "label": "$y=x^2-2x$"}],
    "legend": "auto",
}


def _norm_plot(spec: dict, warnings: list[str]) -> dict:
    out = dict(spec)

    # 别名：xmin/xmax/ymin/ymax → x/y（老写法继续能用）
    for lo_key, hi_key, target in (("xmin", "xmax", "x"), ("ymin", "ymax", "y")):
        if target not in out and lo_key in out and hi_key in out:
            out[target] = [out[lo_key], out[hi_key]]
            warnings.append(f"已把 {lo_key}/{hi_key} 当作 {target} 处理")

    funcs = out.get("functions")
    if funcs is None:
        raise SpecError("plot 缺少 functions：至少给一个函数表达式", PLOT_EXAMPLE)
    if isinstance(funcs, (str, dict)):
        funcs = [funcs]
        warnings.append("functions 传了单个函数，已按只画一条曲线处理")
    if not isinstance(funcs, list) or not funcs:
        raise SpecError("functions 应为非空数组，例如 [{\"expr\": \"x^2\"}]", PLOT_EXAMPLE)

    norm_funcs = []
    for idx, item in enumerate(funcs):
        if isinstance(item, str):
            item = {"expr": item}
        if not isinstance(item, dict):
            raise SpecError(f"functions[{idx}] 应为字符串或对象，实际是 {type(item).__name__}", PLOT_EXAMPLE)
        if "expr" not in item:
            raise SpecError(f"functions[{idx}] 缺少 expr（表达式）", PLOT_EXAMPLE)
        try:
            normalized, fixes = normalize_expr(str(item["expr"]))
            compile_expr(str(item["expr"]))
        except ExprError as e:
            raise SpecError(f"functions[{idx}].expr 有问题：{e}", PLOT_EXAMPLE) from e
        if fixes:
            warnings.append(f"functions[{idx}].expr「{item['expr']}」已自动补乘号 → {normalized}")
        norm_funcs.append({**item, "expr": normalized})
    out["functions"] = norm_funcs

    for key in ("x", "y"):
        if key in out and out[key] is not None:
            pair = out[key]
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise SpecError(f"{key} 应为 [min, max] 两个数字，例如 [-3, 4]", PLOT_EXAMPLE)
            if all(_is_num(v) for v in pair) and float(pair[0]) >= float(pair[1]):
                raise SpecError(f"{key} 的下界必须小于上界（现在 {pair[0]} ≥ {pair[1]}）", PLOT_EXAMPLE)

    for key in ("samples",):
        if key in out and not isinstance(out[key], int):
            raise SpecError(f"{key} 应为整数", PLOT_EXAMPLE)

    legend = out.get("legend", out.get("legend_loc"))
    if legend is not None:
        pos = LEGEND_POSITIONS.get(str(legend).lower())
        if pos is None:
            raise SpecError(
                "legend 只能是 auto / ur / ul / br / bl / none"
                "（也接受 upper right 这类全称）",
                PLOT_EXAMPLE,
            )
        out["legend"] = pos

    for idx, p in enumerate(_expect_list(out, "points", "要标出的点，每项 {x, y, label}", PLOT_EXAMPLE)):
        if not isinstance(p, dict):
            raise SpecError(f"points[{idx}] 应为对象 {{x, y, label}}", PLOT_EXAMPLE)
        for key in ("x", "y"):
            if key not in p or not _is_num(p[key]):
                raise SpecError(f"points[{idx}].{key} 应为数字", PLOT_EXAMPLE)

    pts = out.get("points") or []
    for idx, p in enumerate(pts):
        if "label_offset" in p and "offset" not in p:
            p["offset"] = p["label_offset"]
            warnings.append(f"points[{idx}].label_offset 已按 offset 处理")

    for idx, a in enumerate(_expect_list(out, "asymptotes", "渐近线，每项 {x:..} 或 {y:..}", PLOT_EXAMPLE)):
        if not isinstance(a, dict) or not any(k in a for k in ("x", "y")):
            raise SpecError(f"asymptotes[{idx}] 应为 {{x: 数字}} 或 {{y: 数字}}", PLOT_EXAMPLE)

    return out


# --------------------------------------------------------------------------
# apparatus
# --------------------------------------------------------------------------

APPARATUS_EXAMPLE = {
    "type": "apparatus",
    "parts": [
        {"kind": "iron_stand", "at": [-1.6, 0], "scale": 1.0},
        {"kind": "flask", "at": [0.2, 0.1], "scale": 1.1},
        {"kind": "alcohol_lamp", "at": [0.2, -0.9], "scale": 0.9},
    ],
}


def _norm_apparatus(spec: dict, warnings: list[str]) -> dict:
    out = dict(spec)
    parts = _expect_list(out, "parts", "仪器列表，每项 {kind, at:[x,y], scale}", APPARATUS_EXAMPLE)
    if not parts:
        raise SpecError("apparatus 至少要一个仪器：parts 不能为空", APPARATUS_EXAMPLE)

    # 简写：["beaker", "funnel"] → 自动排成一行
    if all(isinstance(p, str) for p in parts):
        usable = [p for p in parts if p in PARTS]
        unknown = [p for p in parts if p not in PARTS]
        if unknown:
            raise SpecError(
                f"不认识的仪器：{'、'.join(unknown)}"
                f"\n  可用：{', '.join(PARTS)}（连线用 kind='tube' + points）",
                APPARATUS_EXAMPLE,
            )
        step = 1.15
        left = -step * (len(usable) - 1) / 2
        parts = [{"kind": k, "at": [round(left + i * step, 3), 0.0]} for i, k in enumerate(usable)]
        warnings.append("parts 用了字符串简写，已自动从左到右排开；要精确位置请传 {kind, at}")

    norm = []
    for idx, p in enumerate(parts):
        if not isinstance(p, dict):
            raise SpecError(
                f"parts[{idx}] 应为对象 {{kind, at:[x,y], scale}}，不能传 {type(p).__name__}"
                f"｛原样：{str(p)[:30]}｝"
                f"\n  简写也只能整组用字符串：parts: [\"beaker\", \"funnel\"]",
                APPARATUS_EXAMPLE,
            )
        kind = p.get("kind")
        if not isinstance(kind, str):
            raise SpecError(f"parts[{idx}].kind 应为字符串（仪器名）", APPARATUS_EXAMPLE)
        if kind != "tube" and kind not in PARTS:
            raise SpecError(
                f"parts[{idx}].kind = 「{kind}」不认识"
                f"\n  可用：{', '.join(PARTS)}；连线用 tube + points:[[x1,y1],[x2,y2]]",
                APPARATUS_EXAMPLE,
            )
        item = dict(p)
        if "at" in item:
            item["at"] = _expect_pair(item["at"], f"parts[{idx}].at", APPARATUS_EXAMPLE)
        if "scale" in item and not _is_num(item["scale"]):
            raise SpecError(f"parts[{idx}].scale 应为数字", APPARATUS_EXAMPLE)
        if kind == "tube":
            pts = item.get("points")
            if not isinstance(pts, list) or len(pts) < 2:
                raise SpecError(f"parts[{idx}] 是 tube，需要 points: [[x1,y1],[x2,y2],…]", APPARATUS_EXAMPLE)
        norm.append(item)
    out["parts"] = norm

    for idx, note in enumerate(_expect_list(out, "notes", "标注，每项 {text, at, target}", APPARATUS_EXAMPLE)):
        if not isinstance(note, dict) or "text" not in note or "target" not in note or "at" not in note:
            raise SpecError(
                f"notes[{idx}] 应为 {{text, at:[x,y], target:[x,y]}}（at 是文字位置，target 是箭头指向）",
                APPARATUS_EXAMPLE,
            )
    return out


# --------------------------------------------------------------------------
# cell
# --------------------------------------------------------------------------

CELL_EXAMPLE = {
    "type": "cell",
    "kind": "plant",
    "notes": [{"text": "中心体", "at": [2.4, 0.2], "target": [0.2, 0.3]}],
}


def _norm_cell(spec: dict, warnings: list[str]) -> dict:
    out = dict(spec)
    kind = out.get("kind", "plant")
    if kind not in CELL_LABELS:
        raise SpecError(f"kind 只能是 {'/'.join(CELL_LABELS)}（现在 {kind!r}）", CELL_EXAMPLE)
    out["kind"] = kind

    notes = out.get("notes")
    if notes is None:
        notes = []
    elif isinstance(notes, bool):
        raise SpecError(
            "notes 是「标注数组」，不是开关：不想要标注就删掉这个字段",
            {"type": "cell", "kind": kind},
        )
    elif isinstance(notes, (str, dict)):
        notes = [notes]
        warnings.append("notes 传了单项，已按数组处理")
    if not isinstance(notes, list):
        raise SpecError(
            f"notes 应为对象数组，实际是 {type(notes).__name__}"
            f"\n  格式：[{{\"text\": \"中心体\", \"at\": [2.4, 0.2], \"target\": [0.2, 0.3]}}]",
            CELL_EXAMPLE,
        )
    norm_notes = []
    for idx, note in enumerate(notes):
        if not isinstance(note, dict):
            raise SpecError(
                f"notes[{idx}] 应为对象 {{\"text\", \"at\", \"target\"}}，实际是 {type(note).__name__}",
                CELL_EXAMPLE,
            )
        for key in ("text", "at", "target"):
            if key not in note:
                raise SpecError(f"notes[{idx}] 缺少 {key}", CELL_EXAMPLE)
        item = dict(note)
        item["at"] = _expect_pair(item["at"], f"notes[{idx}].at", CELL_EXAMPLE)
        item["target"] = _expect_pair(item["target"], f"notes[{idx}].target", CELL_EXAMPLE)
        norm_notes.append(item)
    out["notes"] = norm_notes

    label_key = "show_builtin_labels"
    if label_key in out and not isinstance(out[label_key], bool):
        raise SpecError(
            f"{label_key} 应为 true/false（默认 true：画内置标签；false：只留你自己标的）",
            {"type": "cell", "kind": kind, label_key: False},
        )
    return out


# --------------------------------------------------------------------------
# 其余模板：只做最基本的形状检查，把最常见的错误提前到渲染前
# --------------------------------------------------------------------------

def _norm_geometry(spec: dict, warnings: list[str]) -> dict:
    example = {"type": "geometry", "points": {"A": [0, 0], "B": [3, 0], "C": [1, 2]},
               "segments": [["A", "B"], ["B", "C"], ["C", "A"]]}
    _require(spec, "points", "点名与坐标，例如 {\"A\":[0,0],\"B\":[3,0]}", example)
    pts = spec["points"]
    if not isinstance(pts, dict):
        raise SpecError("points 应为对象 {点名: [x, y]}", example)
    for name, p in pts.items():
        try:
            _expect_pair(p, f"points[{name}]", example)
        except SpecError:
            raise SpecError(f"points[{name}] 应为 [x, y] 两个数字", example) from None
    return dict(spec)


def _norm_numberline(spec: dict, warnings: list[str]) -> dict:
    example = {"type": "numberline", "min": -3, "max": 3,
               "points": [{"x": -1, "label": "$-1$"}]}
    for key in ("min", "max"):
        if key in spec and not _is_num(spec[key]):
            raise SpecError(f"{key} 应为数字", example)
    if float(spec.get("min", -3)) >= float(spec.get("max", 5)):
        raise SpecError("min 必须小于 max", example)
    for idx, p in enumerate(_expect_list(spec, "points", "点，每项 {x, label}", example)):
        if not isinstance(p, dict) or not _is_num(p.get("x")):
            raise SpecError(f"points[{idx}] 应为 {{x: 数字, label: \"…\"}}", example)
    return dict(spec)


def _norm_venn(spec: dict, warnings: list[str]) -> dict:
    example = {"type": "venn", "sets": [{"label": "A"}, {"label": "B"}],
               "counts": {"Aonly": 3, "Bonly": 2, "AB": 1}}
    sets = _expect_list(spec, "sets", "集合，每项 {label, color}", example)
    if sets and not all(isinstance(s, dict) for s in sets):
        raise SpecError("sets 应为对象数组：[{\"label\":\"A\"},{\"label\":\"B\"}]", example)
    if not (1 <= len(sets) <= 3):
        raise SpecError(f"sets 目前支持 1—3 个集合（现在 {len(sets)} 个）", example)
    return dict(spec)


def _norm_flow(spec: dict, warnings: list[str]) -> dict:
    example = {"type": "flow", "steps": ["光反应", "暗反应"], "layout": "horizontal"}
    steps = _expect_list(spec, "steps", "步骤，字符串或 {text, color}", example)
    if not steps:
        raise SpecError("flow 至少需要一个步骤", example)
    for idx, s in enumerate(steps):
        if not isinstance(s, (str, dict)):
            raise SpecError(f"steps[{idx}] 应为字符串或 {{text}}", example)
    return dict(spec)


def _norm_molecule(spec: dict, warnings: list[str]) -> dict:
    example = {"type": "molecule", "smiles": "CCO", "label": "乙醇"}
    _require(spec, "smiles", "分子的 SMILES，例如 CCO", example)
    if not isinstance(spec["smiles"], str):
        raise SpecError("smiles 应为字符串，例如 \"CCO\"", example)
    return dict(spec)


def _norm_circuit(spec: dict, warnings: list[str]) -> dict:
    example = {"type": "circuit", "nodes": {"A": [0, 0], "B": [5, 0]},
               "elements": [{"kind": "battery", "from": "A", "to": "B"}]}
    _require(spec, "nodes", "节点坐标 {\"A\":[0,0]}", example)
    if not isinstance(spec["nodes"], dict):
        raise SpecError("nodes 应为对象 {点名: [x, y]}", example)
    for name, p in spec["nodes"].items():
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise SpecError(f"nodes[{name}] 应为 [x, y]", example)
    els = _expect_list(spec, "elements", "元件，每项 {kind, from, to}", example)
    if not els:
        raise SpecError("circuit 至少需要一个元件", example)
    for idx, e in enumerate(els):
        if not isinstance(e, dict) or "kind" not in e:
            raise SpecError(f"elements[{idx}] 应为 {{kind, from, to}}", example)
    return dict(spec)


def _norm_force(spec: dict, warnings: list[str]) -> dict:
    example = {"type": "force", "body": {"at": [0, 0], "label": "$m$"},
               "forces": [{"angle": 270, "magnitude": 3, "label": "$mg$"}]}
    _require(spec, "forces", "力列表，每项 {angle, magnitude, label}", example)
    for idx, f in enumerate(_expect_list(spec, "forces", "力", example)):
        if not isinstance(f, dict) or not _is_num(f.get("angle")):
            raise SpecError(f"forces[{idx}].angle 应为数字（角度制：0° 向右，90° 向上）", example)
    return dict(spec)


def _norm_incline(spec: dict, warnings: list[str]) -> dict:
    example = {"type": "incline", "angle": 30, "decompose": True}
    if "angle" in spec and not _is_num(spec["angle"]):
        raise SpecError("angle 应为数字（倾角，单位度）", example)
    return dict(spec)


def _norm_optics(spec: dict, warnings: list[str]) -> dict:
    example = {"type": "optics", "focal": 2, "object_distance": 3, "object_height": 1}
    for key in ("focal", "object_distance", "object_height"):
        if key not in spec:
            raise SpecError(f"optics 缺少 {key}", example)
        if not _is_num(spec[key]):
            raise SpecError(f"{key} 应为数字", example)
    return dict(spec)


def _norm_grid(spec: dict, warnings: list[str]) -> dict:
    example = {"type": "grid", "chars": ["永", "和"], "pinyin": ["yǒng", "hé"]}
    chars = spec.get("chars")
    if isinstance(chars, str):
        spec = {**spec, "chars": list(chars)}
        warnings.append("chars 传了字符串，已拆成单字")
        chars = spec["chars"]
    if not isinstance(chars, list) or not chars:
        raise SpecError("grid 需要 chars：要练的字，例如 [\"永\", \"和\"]", example)
    pinyin = spec.get("pinyin")
    if pinyin is not None and (not isinstance(pinyin, list) or len(pinyin) != len(chars)):
        raise SpecError(
            f"pinyin 应为与 chars 等长的数组（chars {len(chars)} 个，pinyin "
            f"{len(pinyin) if isinstance(pinyin, list) else type(pinyin).__name__}）",
            example,
        )
    return dict(spec)


_NORM = {
    "plot": _norm_plot,
    "apparatus": _norm_apparatus,
    "cell": _norm_cell,
    "geometry": _norm_geometry,
    "numberline": _norm_numberline,
    "venn": _norm_venn,
    "flow": _norm_flow,
    "molecule": _norm_molecule,
    "circuit": _norm_circuit,
    "force": _norm_force,
    "incline": _norm_incline,
    "optics": _norm_optics,
    "grid": _norm_grid,
}


def normalize(spec) -> tuple[dict, list[str], dict]:
    """校验并归一化一个图示 spec。

    Returns:
        (spec_out, warnings, info)

    Raises:
        SpecError: 带中文说明与最小示例。
    """
    if not isinstance(spec, dict):
        raise SpecError(
            f"spec 应为对象，实际是 {type(spec).__name__}",
            {"type": "incline", "angle": 30},
        )
    kind = spec.get("type")
    if not kind:
        raise SpecError(
            f"spec.type 缺少模板名；可用：{', '.join(TEMPLATES)}",
            {"type": "plot", "functions": [{"expr": "x**2"}]},
        )
    if kind not in _NORM:
        raise SpecError(
            f"未知模板「{kind}」；可用：{', '.join(TEMPLATES)}",
            {"type": "incline", "angle": 30},
        )

    warnings: list[str] = []
    out = _NORM[kind](spec, warnings)
    out["type"] = kind

    info = {"template": kind}
    if kind == "plot":
        info["functions"] = [f["expr"] for f in out.get("functions", [])]
        info["x"] = out.get("x")
        info["y"] = out.get("y")
        info["legend"] = out.get("legend", "auto")
    elif kind == "cell":
        info["kind"] = out.get("kind")
        info["builtin_labels"] = [
            {"text": t, "at": at, "target": target}
            for t, target, at in CELL_LABELS[out.get("kind", "plant")]
        ]
        info["builtin_labels_visible"] = out.get("show_builtin_labels", True)
    elif kind == "apparatus":
        info["parts"] = [p["kind"] for p in out.get("parts", [])]
    return out, warnings, info
