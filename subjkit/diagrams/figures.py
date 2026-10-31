# -*- coding: utf-8 -*-
"""图示统一入口：按 spec["type"] 分派。

流程固定为「先校验归一化，再画」：所有参数问题在这里变成中文提示，
模板函数只负责画，不再猜参数。
"""
from __future__ import annotations

from pathlib import Path

from . import bio, chem, chinese, mathfig, physics
from .base import finish
from .validate import SpecError, normalize

TEMPLATES = {
    "circuit": physics.circuit,
    "force": physics.force,
    "incline": physics.incline,
    "optics": physics.optics,
    "plot": mathfig.plot,
    "geometry": mathfig.geometry,
    "numberline": mathfig.numberline,
    "venn": mathfig.venn,
    "apparatus": chem.apparatus,
    "cell": bio.cell,
    "flow": bio.flow,
    "grid": chinese.grid,
}

TEMPLATE_DOCS = {
    "circuit": "电路图：nodes 坐标 + elements（battery/resistor/lamp/switch/ammeter/voltmeter/capacitor/rheostat/fuse/motor）",
    "force": "受力图：body 方块/圆 + forces（angle 角度、magnitude 大小、label 标签）",
    "incline": "斜面：angle 倾角 + 重力/支持力/摩擦力，decompose=true 画重力分解",
    "optics": "凸透镜成像光路：focal 焦距、object_distance 物距、object_height 物高",
    "plot": "函数图像：functions（表达式支持 sin/cos/sqrt/log/abs，^ 表示乘方，乘号可省略）",
    "geometry": "平面几何：points 点名坐标 + segments/polygons/circles/angles/right_angles/ticks",
    "numberline": "数轴：min/max、points 点、intervals 区间",
    "venn": "韦恩图：sets 集合、counts 各区域数字",
    "apparatus": "化学装置：parts 仪器（beaker/flask/round_flask/test_tube/gas_jar/trough/funnel/alcohol_lamp/iron_stand/condenser/thermometer），可整组用字符串简写",
    "cell": "细胞示意图：kind=plant/animal，notes 自定义标注（对象数组），show_builtin_labels 可关内置标签",
    "flow": "流程框图：steps 步骤，layout=horizontal/vertical",
    "grid": "田字格/米字格：chars 汉字、pinyin 拼音、cols 列数",
    "molecule": "分子结构式：smiles + label（输出 .svg 或 .png）",
}


def prepare(spec: dict) -> tuple[dict, list[str], dict]:
    """校验并归一化 spec；`--dry-run` 与 `render` 共用。

    Returns:
        (spec_out, warnings, info)

    Raises:
        SpecError: 消息已是中文，可直接给使用者看。
    """
    return normalize(spec)


def render_normalized(spec: dict, out: str | Path, dpi: int = 300) -> Path:
    """已经过 `prepare()` 的 spec，直接出图。"""
    kind = spec.get("type")
    if kind == "molecule":
        return chem.molecule(spec, out)
    fn = TEMPLATES.get(kind or "")
    if fn is None:
        raise SpecError(
            f"未知图示类型：{kind}（可用：{', '.join(sorted(set(TEMPLATES) | {'molecule'}))}）"
        )
    fig = fn(spec)
    return finish(fig, out, dpi=dpi)


def render(spec: dict, out: str | Path, dpi: int = 300) -> Path:
    """校验 + 出图，一步到位（命令行与测试用）。"""
    normalized, _warnings, _info = prepare(spec)
    return render_normalized(normalized, out, dpi=dpi)
