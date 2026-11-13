# -*- coding: utf-8 -*-
"""针对「中央控制会话」实测问题的回归测试。

每条都对应一条具体反馈，改坏了会在这里红：
    P0-1 check 在数据文档上误报        → 分级 + profile
    P0-2 图示参数报错不可诊断          → 中文 SpecError + 简写/别名
    P1-1 plot 图例压曲线、无位置参数   → legend auto
    P1-2 plot 无刻度、y 要手给         → ticks / xstep / 自动值域
    P1-3 cell 自定义标注压内置标签     → show_builtin_labels + 自动避让
    P2-3 表格跨页策略不明确            → thead 重复 + keep 语义
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from subjkit.check import counts, report, scan  # noqa: E402
from subjkit.diagrams.bio import CELL_LABELS, _place  # noqa: E402
from subjkit.diagrams.expr import ExprError, normalize_expr  # noqa: E402
from subjkit.diagrams.figures import prepare, render  # noqa: E402
from subjkit.diagrams.mathfig import _pick_legend  # noqa: E402
from subjkit.diagrams.validate import SpecError  # noqa: E402
from subjkit.doc import _pdf_failure_message, build_pdf, read_css  # noqa: E402
from subjkit.md2html import build_html, md_to_html  # noqa: E402

OUT = ROOT / "示例" / "输出" / "回归"
OUT.mkdir(parents=True, exist_ok=True)

CHECKS: list[tuple[str, callable]] = []


def case(name: str):
    def wrap(fn):
        CHECKS.append((name, fn))
        return fn
    return wrap


# --------------------------------------------------------------------------
# P0-1 数据文档不再误报
# --------------------------------------------------------------------------
DATA_DOC = "\n".join([
    "| 班级 | 排名 | 上次 |",
    "|---|---|---|",
    "| 一班 | 274/450 | 405/600 |",
    "",
    "整体 A → B，误差 ≈ 3%，覆盖率 ≥ 80%。",
    "判别式 √(b²-4ac)。",
])


@case("P0-1 数据文档：paper 有 error，report 0 error，exclude-ratios 去噪")
def _p01():
    paper = scan(DATA_DOC, profile="paper")
    data = scan(DATA_DOC, profile="report")
    assert counts(paper)["error"] > 0, "paper 模式应把 ≈ 之类算作 error"
    assert counts(data)["error"] == 0, f"report 模式不应有 error：{counts(data)}"
    assert counts(data)["info"] > 0, "report 模式应把数字比值降级为 info"

    ratios = [f for f in data if f.get("numeric_ratio")]
    assert ratios, "本用例应包含 274/450 这类数字比值"
    assert all(f["level"] == "info" for f in ratios), "数字比值在 report 里必须是 info"

    strict = scan(DATA_DOC, profile="report", exclude_ratios=True)
    assert not any(f.get("numeric_ratio") for f in strict), "exclude_ratios 之后不该再有数字比值"
    return f"paper error {counts(paper)['error']} / report error 0（info {counts(data)['info']}）"


@case("P0-1 中文正文里的 → 在 report 里是 info，不是 error")
def _p01b():
    f = [x for x in scan("结论 A → B。", profile="report") if x["char"] == "→"]
    assert f and f[0]["level"] == "info"
    return "→ 降级为 info"


# --------------------------------------------------------------------------
# P0-2 参数报错可诊断
# --------------------------------------------------------------------------
@case("P0-2 apparatus：字符串简写能跑，坏 instrument 报中文")
def _p02a():
    spec, warns, _ = prepare({"type": "apparatus", "parts": ["beaker", "funnel"]})
    assert len(spec["parts"]) == 2 and warns, "简写应被展开并给出说明"
    assert spec["parts"][0]["at"][0] < spec["parts"][1]["at"][0], "简写要按从左到右排"
    try:
        prepare({"type": "apparatus", "parts": [{"kind": "nope"}]})
    except SpecError as e:
        assert "不认识" in str(e)
        return "简写可用；坏 kind 报中文"
    raise AssertionError("坏 kind 应抛 SpecError")


@case("P0-2 cell：notes 传 true 报「标注数组」，并给示例")
def _p02b():
    try:
        prepare({"type": "cell", "kind": "plant", "notes": True})
    except SpecError as e:
        msg = str(e)
        assert "标注数组" in msg and "可用示例" in msg
        return "notes=true 给出中文说明 + 示例"
    raise AssertionError("notes=true 应抛 SpecError")


@case("P0-2 plot：缺乘号自动补、xmin/xmax 兼容、xy 报歧义")
def _p02c():
    spec, warns, _ = prepare({
        "type": "plot", "functions": ["x^2-2x-3"], "xmin": -2, "xmax": 4,
    })
    assert spec["functions"][0]["expr"] == "x**2-2*x-3"
    assert spec["x"] == [-2, 4]
    assert any("补乘号" in w for w in warns)
    assert any("xmin/xmax" in w for w in warns)

    try:
        normalize_expr("xy")
    except ExprError as e:
        assert "歧义" in str(e)
    else:
        raise AssertionError("xy 应报歧义")
    return "2x→2*x、xmin→x、xy 报歧义"


@case("P0-2 所有报错都不含 Python 类型名")
def _p02d():
    bad = [
        {"type": "apparatus", "parts": ["nope"]},
        {"type": "cell", "kind": "nope"},
        {"type": "plot", "functions": [{"expr": "2x"}], "x": [5, 1]},
        {"type": "geometry", "points": {"A": "B"}},
        {"type": "flow", "steps": []},
        {"type": "molecule"},
        {"type": "没有这个模板"},
    ]
    for spec in bad:
        try:
            prepare(spec)
        except SpecError as e:
            msg = str(e)
            assert "Traceback" not in msg and "object is not" not in msg, msg
        else:
            raise AssertionError(f"应报错：{spec}")
    return f"{len(bad)} 种坏 spec 都给出中文说明"


# --------------------------------------------------------------------------
# P1-1 图例避让
# --------------------------------------------------------------------------
@case("P1-1 legend=auto 会把图例挪到曲线不经过的角")
def _p11():
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.pyplot import subplots

    fig, ax = subplots()
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    # 曲线只在上半部（左上、右上都有点），左下是空的
    samples = [(x * 0.1, 8 + (x * 0.1 - 5) ** 2 * 0.1) for x in range(100)]
    picked = _pick_legend(ax, samples, [])
    assert picked in ("lower left", "lower right"), f"应挑下方角落，实际 {picked}"
    spec, _w, _i = prepare({
        "type": "plot", "functions": [{"expr": "x^2-2*x", "label": "$y=x^2-2x$"}],
        "x": [-3, 4], "legend": "ur",
    })
    assert spec["legend"] == "upper right"
    spec2, _w2, _i2 = prepare({
        "type": "plot", "functions": [{"expr": "x"}], "legend": "none",
    })
    assert spec2["legend"] == "none"
    return f"auto 选中 {picked}；ur/none 原样保留"


@case("P1-1 points[].label_offset 生效")
def _p11b():
    spec, warns, _ = prepare({
        "type": "plot", "functions": [{"expr": "x"}],
        "points": [{"x": 1, "y": 1, "label": "$P$", "label_offset": [0.3, -0.6]}],
    })
    assert spec["points"][0]["offset"] == [0.3, -0.6]
    assert any("label_offset" in w for w in warns)
    return "label_offset → offset"


# --------------------------------------------------------------------------
# P1-2 刻度与值域
# --------------------------------------------------------------------------
@case("P1-2 刻度/网格/步长参数存在，y 省略时自动值域")
def _p12():
    from subjkit.diagrams.mathfig import plot as plot_fig

    spec, _w, _i = prepare({
        "type": "plot", "x": [-2, 2],
        "functions": [{"expr": "x^2-1"}],
        "ticks": True, "grid": True, "xstep": 1, "ystep": 2,
    })
    fig = plot_fig(spec)
    ax = fig.axes[0]
    assert ax.axison, "函数图像必须打开坐标轴（原来被 new_figure 关掉了）"
    lo, hi = ax.get_ylim()
    assert lo < -1 and hi > 3, f"y 值域应自动覆盖函数值：{[lo, hi]}"
    labels = [t.get_visible() for t in ax.get_xticklabels()]
    assert any(labels), "刻度标签应可见"
    return f"y 自动值域 [{lo:.1f}, {hi:.1f}]，刻度可见"


# --------------------------------------------------------------------------
# P1-3 cell 标签
# --------------------------------------------------------------------------
@case("P1-3 自定义标注会避开内置标签；可整组关掉内置标签")
def _p13():
    builtin = [(float(at[0]), float(at[1])) for _t, _target, at in CELL_LABELS["plant"]]
    # 正好压在线粒体上的位置
    near = CELL_LABELS["plant"][3][2]
    placed = _place(list(near), builtin)
    assert placed != list(near), "压在内置标签上的自定义标注应被挪开"
    assert all(abs(placed[1] - y) > 0.19 for _x, y in builtin), "挪开后不能还压着"

    spec, _w, info = prepare({"type": "cell", "kind": "plant", "show_builtin_labels": False})
    assert spec["show_builtin_labels"] is False
    assert info["builtin_labels_visible"] is False
    assert len(info["builtin_labels"]) == len(CELL_LABELS["plant"])
    return f"标注从 {list(near)} 挪到 {placed}"


# --------------------------------------------------------------------------
# P2-3 表格分页
# --------------------------------------------------------------------------
@case("P2-3 表格有 thead（跨页重复表头），<!--keep--> 包住下一块")
def _p23():
    css = (ROOT / "assets" / "base.css").read_text(encoding="utf-8")
    assert "display: table-header-group" in css, "表头需要在每页重复"
    assert ".keep" in css

    md = "\n".join([
        "<!--keep-->",
        "| 甲 | 乙 |",
        "|---|---|",
        "| 1 | 2 |",
    ])
    html = md_to_html(md, ROOT)
    assert '<div class="keep"><table>' in html, f"keep 标记没生效：{html[:120]}"

    plain = md_to_html("| 甲 |\n|---|\n| 1 |", ROOT)
    assert "keep" not in plain, "没写 keep 就不该套"
    assert "<thead>" in plain, "表格必须带 thead"

    doc, _meta = build_html(md, ROOT, css, {})
    assert "table-header-group" in doc
    return "thead 重复 + keep 语义"


# --------------------------------------------------------------------------
# 0.3.1 实测反馈（引用块标题 / 硬换行 / 行文比较符 / BOM / 报错可诊断）
# --------------------------------------------------------------------------
@case("必修1 引用块里的 ## 按标题渲染，不再原样印出")
def _b1():
    md = "\n".join([
        "> ## ★ 引用块里的二级标题",
        ">",
        "> 正文一行。",
    ])
    html = md_to_html(md, ROOT)
    assert "<blockquote>" in html, html
    assert "<h2>" in html, f"引用块里的标题没被解析：{html}"
    assert "##" not in html, f"markdown 记号被印到纸上了：{html}"
    assert "<p>正文一行。</p>" in html, "引用块里的两行不该粘成一段"

    # 引用块里的列表也要成立
    html2 = md_to_html("> 列表：\n> - 一\n> - 二", ROOT)
    assert "<ul>" in html2 and "<li>一</li>" in html2, html2
    return "## → <h2>，段落不再粘连"


@case("必修2 行尾两个空格 = 硬换行（不再需要手写 <br>）")
def _b2():
    md = "A. 甲选项  \nB. 乙选项  \nC. 丙选项  \nD. 丁选项"
    html = md_to_html(md, ROOT)
    assert html.count("<br>") == 3, f"应有 3 个 <br>，实际：{html}"
    assert "A. 甲选项<br>B. 乙选项" in html

    # 没有行尾空格时仍然合并（中文行之间不插空格）
    merged = md_to_html("甲行\n乙行", ROOT)
    assert "<br>" not in merged and "甲行乙行" in merged, merged

    # 引用块里的硬换行也要生效
    quoted = md_to_html("> 甲  \n> 乙", ROOT)
    assert "<br>" in quoted, quoted
    return "3 个 <br>；无空格仍合并；引用块内也生效"


@case("必修3 行文里的 ≥ ≤ ≠ 只 warn，不拦 PDF；数学语境仍 error")
def _b3():
    prose = scan("用时 ≥ 20 分钟。\n成绩≤90 分。\n（≥60 分）", profile="paper")
    assert counts(prose)["error"] == 0, f"行文比较符不该拦：{counts(prose)}"
    assert counts(prose)["warn"] == 3

    math = scan("当 x ≥ 1 时成立。\n≤20", profile="paper")
    assert counts(math)["error"] == 2, f"变量/行首的 ≥ 仍应 error：{counts(math)}"

    # 混在一份卷子里：只有数学语境那行会拦
    mixed = scan("用时 ≥ 20 分钟。\n当 x ≥ 1 时成立。", profile="paper")
    assert counts(mixed)["error"] == 1, counts(mixed)
    return "行文 3 条 warn / 数学 2 条 error / 混合 1 条 error"


@case("必修3 端到端：带「用时 ≥ 20 分钟」的卷子能出 PDF")
def _b3b():
    md = "\n".join([
        "---", "title: 行文符号验收", "---", "",
        "1. 用时 ≥ 20 分钟。", "", "2. 成绩 ≤ 90 分。",
    ])
    src = OUT / "行文符号.md"
    src.write_text(md, encoding="utf-8")
    findings = scan(md, profile="paper")
    assert counts(findings)["error"] == 0, counts(findings)
    out = OUT / "行文符号.pdf"
    result = build_pdf(src, out)
    assert result["pages"] >= 1 and not result["math_errors"]
    return f"{result['pages']} 页，error 0，正常出图"


@case("隐患4 read_css 遇 BOM 自动剥掉（否则整段样式失效）")
def _b4():
    tmp = OUT / "bom.css"
    tmp.write_bytes("\ufeffbody{font-size:12pt}\n.keep{break-inside:avoid}".encode("utf-8"))
    css = read_css(tmp)
    assert not css.startswith("\ufeff"), "BOM 没被剥掉"
    assert css.lstrip().startswith("body{"), css[:40]
    # 真实样式文件本身也必须是干净的
    assert not read_css().startswith("\ufeff")
    return "utf-8-sig 生效"


@case("报告摘要行：一眼看出 error 会不会拦")
def _b5():
    text = report(scan("√(b²-4ac)", profile="paper"), "x.md", profile="paper")
    assert text.startswith("error "), text[:60]
    assert "会拦截出 PDF" in text.splitlines()[0], text.splitlines()[0]
    assert "不拦截，可改可不改" in text.splitlines()[0]

    clean = report(scan("用时 ≥ 20 分钟。", profile="paper"), "y.md", profile="paper")
    assert "不拦截" in clean.splitlines()[0], clean.splitlines()[0]
    assert "error 0 处" in clean.splitlines()[0]
    return clean.splitlines()[0]


@case("Edge 出不来 PDF 时，报错带路径 + 目录可写性 + 全量 stderr")
def _b6():
    msg = _pdf_failure_message(OUT / "无.pdf", Path(tempfile.gettempdir()) / "kt_x",
                               0, "Failed to write file /tmp/x.pdf\nsecond line")
    assert "输出路径" in msg and "无.pdf" in msg, msg
    assert "输出目录" in msg and ("可写" in msg or "不可写" in msg), msg
    assert "exit=0" in msg, "必须保留退出码，exit=0 是最误导的那个信息"
    assert "Failed to write" in msg, "stderr 要全量带上（原来截 600 字常常是空的）"
    assert "second line" in msg, "stderr 多行都要带上"

    empty = _pdf_failure_message(OUT / "无.pdf", Path("C:/x"), 0, "")
    assert "stderr 是空的" in empty, "stderr 为空时要给出下一步，而不是空着"
    return "路径 / 目录状态 / 全量 stderr 都在"


def main() -> int:
    failures = 0
    for name, fn in CHECKS:
        try:
            detail = fn()
            print(f"✔ {name}" + (f"　—— {detail}" if detail else ""))
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"✘ {name}\n    {type(e).__name__}: {e}")
    print(f"\n{'✔ 回归全部通过' if not failures else f'✘ {failures} 项失败'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
