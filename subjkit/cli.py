# -*- coding: utf-8 -*-
"""学科工具命令行。"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

from .check import counts as check_counts
from .check import report as check_report
from .check import scan as check_scan
from .doc import ASSETS, build_pdf, edge_exe, node_exe
from .diagrams.figures import TEMPLATES, TEMPLATE_DOCS, prepare as prepare_fig
from .diagrams.figures import render_normalized as render_fig
from .diagrams.validate import SpecError


def _write_raw(args, payload: dict) -> None:
    path = getattr(args, "result_json", None)
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_result(args, cmd: str, data) -> None:
    """把机器可读的结果写到 --result-json。

    DSH 插件用 `stdio: 'ignore'` 起子进程（沙箱里管道可能 EPERM），所以 stdout
    一个字节都拿不到；结果必须落盘。`{"ok": true, "cmd": ..., "data": ...}`
    是成功信封，失败时 main() 会写 `{"ok": false, "cmd": ..., "error": ...}`。
    """
    path = getattr(args, "result_json", None)
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ok": True, "cmd": cmd, "data": data}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_error(args, error: BaseException) -> None:
    path = getattr(args, "result_json", None)
    if not path:
        return
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ok": False,
            "cmd": getattr(args, "cmd", None),
            "error": f"{type(error).__name__}: {error}",
        }
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass  # 连错误都写不进去时，只能靠退出码


def _print_pdf_result(result: dict) -> None:
    print(f"✔ PDF：{result['pdf']}")
    print(f"  页数：{result['pages']}　公式：{result['formulas']} 条")
    if result.get("odd"):
        print(f"  奇数页：{result['odd']}")
        print(f"  偶数页：{result['even']}")
    for p in result.get("previews", []):
        print(f"  预览：{p}")
    errs = result.get("math_errors") or []
    if errs:
        print(f"  ⚠ 有 {len(errs)} 条公式没排好，请改 TeX：")
        for e in errs[:20]:
            print(f"    - {e.get('message')}　<< {e.get('tex')}")


def cmd_pdf(args) -> int:
    meta = {}
    if args.title:
        meta["title"] = args.title
    if args.subtitle:
        meta["subtitle"] = args.subtitle
    if args.banner:
        meta["banner"] = args.banner
    if args.footer:
        meta["footer"] = args.footer
    inp = Path(args.input)
    out = Path(args.out) if args.out else inp.with_suffix(".pdf")

    # 出卷前的自检：默认先跑 check，有 error 就不出 PDF。
    # 规则见 04_规则（AI看）/学科工具规范.md：「check 不 0，不许出 PDF」。
    check_result = None
    if args.check_only or not args.no_check:
        text = inp.read_text(encoding="utf-8")
        findings = check_scan(text, profile="paper")
        c = check_counts(findings)
        check_result = {
            "count": c["total"], "error": c["error"], "warn": c["warn"],
            "info": c["info"], "findings": findings[:200],
            "report": check_report(findings, str(inp), profile="paper"),
        }
        if args.check_only:
            _write_raw(args, {"ok": True, "cmd": "pdf", "data": {"check": check_result}})
            print(check_result["report"])
            return 0 if c["error"] == 0 else 1
        if c["error"]:
            _write_raw(args, {
                "ok": False,
                "cmd": "pdf",
                "error": (f"check 拦下 {c['error']} 处 error，未生成 PDF。"
                          "先修到 0 处；确认要跳过就传 --no-check（或工具参数 check: false）。\n"
                          + check_result["report"]),
                "data": {"check": check_result},
            })
            print(f"✘ check 拦下 {c['error']} 处 error，未生成 PDF；详见下面的报告",
                  file=sys.stderr)
            print(check_result["report"])
            return 3

    preview = None
    if args.preview is not None:
        preview = Path(args.preview) if args.preview not in ("", "__auto__") else out.with_name(out.stem + "_预览.png")
    pages = None
    if args.preview_pages:
        pages = [int(x) for x in args.preview_pages.replace("，", ",").split(",") if x.strip()]

    result = build_pdf(
        inp, out, meta=meta, keep_html=args.keep_html, split=args.split,
        preview=preview, preview_pages=pages,
    )
    if check_result:
        result["check"] = {k: check_result[k] for k in ("count", "error", "warn", "info")}
    _write_result(args, "pdf", result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_pdf_result(result)
    if check_result and check_result["warn"]:
        print(f"  （另有 {check_result['warn']} 处 warn，未拦截）")
    return 0


def _load_spec(args) -> dict:
    if args.spec:
        return json.loads(Path(args.spec).read_text(encoding="utf-8-sig"))
    if args.json:
        return json.loads(args.json)
    if args.stdin:
        return json.loads(sys.stdin.read())
    raise SystemExit("需要 --spec 文件、--json 字符串或 --stdin")


def cmd_fig(args) -> int:
    spec = _load_spec(args)
    if args.template:
        spec["type"] = args.template
    out = Path(args.out)
    if out.suffix.lower() not in (".svg", ".png"):
        out = out.with_suffix(".svg")

    normalized, warnings, info = prepare_fig(spec)

    if args.dry_run:
        result = {"dry_run": True, "template": info["template"], "info": info,
                  "warnings": warnings, "would_write": str(out.resolve())}
        _write_result(args, "fig", result)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"✔ spec 校验通过：{info['template']}（未出图，--dry-run）")
            for w in warnings:
                print(f"  · {w}")
            if "builtin_labels" in info:
                print("  内置标签位置（挑空位加 notes.at）：")
                for item in info["builtin_labels"]:
                    print(f"    {item['text']}  at={item['at']}")
        return 0

    produced = Path(render_fig(normalized, out, dpi=args.dpi)).resolve()
    result = {
        "out": str(produced),
        "type": normalized["type"],
        "format": produced.suffix.lstrip(".").lower(),
        "dpi": args.dpi,
        "bytes": produced.stat().st_size if produced.exists() else None,
        "warnings": warnings,
    }
    _write_result(args, "fig", result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"✔ 图示：{produced}")
        for w in warnings:
            print(f"  · {w}")
    return 0


def cmd_math(args) -> int:
    import subprocess

    out = Path(args.out)
    if out.suffix.lower() != ".svg":
        out = out.with_suffix(".svg")
    try:
        proc = subprocess.run(
            [node_exe(), str(ASSETS / "render_math.mjs"), "--tex", args.tex,
             "--out", str(out), *(["--display"] if args.display else [])],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )
    except subprocess.TimeoutExpired:
        print("✘ 公式渲染超时（120 秒）", file=sys.stderr)
        return 2
    if proc.returncode != 0:
        print(f"✘ 公式渲染失败：{proc.stderr[-400:] or proc.stdout[-400:]}", file=sys.stderr)
        return 2
    print(f"✔ 公式：{out}")
    return 0


def cmd_check(args) -> int:
    src = Path(args.input)
    text = sys.stdin.read() if str(src) == "-" else src.read_text(encoding="utf-8")
    label = None if str(src) == "-" else str(src)
    findings = check_scan(text, profile=args.profile, exclude_ratios=args.exclude_ratios)
    c = check_counts(findings)
    shown = findings[:200]
    report = check_report(findings, label, profile=args.profile)
    result = {
        "input": label,
        "profile": args.profile,
        "count": c["total"],
        "error": c["error"],
        "warn": c["warn"],
        "info": c["info"],
        "actionable": c["actionable"],
        "truncated": max(0, len(findings) - len(shown)),
        "findings": shown,
        "report": report,
        "strict": bool(args.strict),
    }
    _write_result(args, "check", result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(report)
    return 1 if (args.strict and c["actionable"]) else 0


def cmd_doctor(args) -> int:
    print("学科工具自检")
    print(f"  Python：{sys.version.split()[0]}")
    ok = True
    for mod in ("matplotlib", "numpy", "pypdf", "pymupdf", "rdkit"):
        found = importlib.util.find_spec(mod) is not None
        ok &= found
        print(f"  {mod:<12}{'✔' if found else '✘ 未安装'}")
    try:
        print(f"  node：{node_exe()}")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"  node：✘ {e}")
    mj = ASSETS / "render_math.mjs"
    mj_ok = mj.exists() and (ASSETS.parent / "node_modules" / "mathjax-full").exists()
    ok &= mj_ok
    print(f"  MathJax：{'✔' if mj_ok else '✘ 未安装（在工具目录执行 npm install）'}")
    try:
        print(f"  Edge：{edge_exe()}")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"  Edge：✘ {e}")
    print("\n图示模板：")
    for name, fn in sorted(TEMPLATES.items()):
        print(f"  {name:<12}{TEMPLATE_DOCS.get(name, '')}")
    print(f"  {'molecule':<12}{TEMPLATE_DOCS['molecule']}")
    print("\n结论：" + ("✔ 全部可用" if ok else "✘ 有缺项，见上"))
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="subjkit.py",
        description="学科材料排版：公式（LaTeX→矢量）、试卷 PDF、物理/数学/化学/生物/语文图示。",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("pdf", help="Markdown → PDF（公式自动转矢量）")
    pp.add_argument("input", help="输入 .md")
    pp.add_argument("-o", "--out", help="输出 .pdf（默认同名）")
    pp.add_argument("--title")
    pp.add_argument("--subtitle")
    pp.add_argument("--banner")
    pp.add_argument("--footer")
    pp.add_argument("--split", action="store_true", help="另存奇数页/偶数页两个 PDF")
    pp.add_argument("--preview", nargs="?", const="__auto__", help="同时导出 PNG 预览（默认首页）")
    pp.add_argument("--preview-pages", help="预览页码，如 1,2")
    pp.add_argument("--keep-html", action="store_true", help="保留渲染后的 HTML 便于排查")
    pp.add_argument("--no-check", action="store_true", help="跳过出 PDF 前的自动 check")
    pp.add_argument("--check-only", action="store_true", help="只跑 check，不出 PDF")
    pp.add_argument("--json", action="store_true")
    pp.add_argument("--result-json", help="把结果写成 JSON 文件（DSH 插件用，不依赖 stdout）")
    pp.set_defaults(func=cmd_pdf)

    pf = sub.add_parser("fig", help="生成图示（SVG/PNG，矢量）")
    pf.add_argument("template", nargs="?", help="图示类型，如 circuit/force/plot")
    pf.add_argument("-o", "--out", default="图.svg")
    pf.add_argument("--spec", help="JSON 参数文件")
    pf.add_argument("--json", help="直接给 JSON 字符串")
    pf.add_argument("--stdin", action="store_true", help="从标准输入读 JSON")
    pf.add_argument("--dpi", type=int, default=300)
    pf.add_argument("--dry-run", action="store_true", help="只校验 spec，不出图")
    pf.add_argument("--result-json", help="把结果写成 JSON 文件（DSH 插件用）")
    pf.set_defaults(func=cmd_fig)

    pm = sub.add_parser("math", help="单条公式 → SVG")
    pm.add_argument("tex")
    pm.add_argument("-o", "--out", default="formula.svg")
    pm.add_argument("--display", action="store_true")
    pm.set_defaults(func=cmd_math)

    pc = sub.add_parser("check", help="检查正文里的裸数学符号（√、∈、1/2 等）")
    pc.add_argument("input", help=".md 文件，或 - 表示标准输入")
    pc.add_argument("--strict", action="store_true", help="有 error/warn 时返回非零退出码（info 不算）")
    pc.add_argument("--profile", choices=["paper", "report"], default="paper",
                    help="paper=出卷，严格（默认）；report=数据报告，比值与行文箭头降级为 info")
    pc.add_argument("--exclude-ratios", action="store_true", help="跳过「纯数字/纯数字」形态（274/450）")
    pc.add_argument("--json", action="store_true", help="把结果打成 JSON 输出")
    pc.add_argument("--result-json", help="把结果写成 JSON 文件（DSH 插件用）")
    pc.set_defaults(func=cmd_check)

    pd = sub.add_parser("doctor", help="自检依赖与模板")
    pd.set_defaults(func=cmd_doctor)
    return p


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        # 插件拿不到 stderr（stdio 忽略），失败原因必须写进结果文件。
        _write_error(args, e)
        if os.environ.get("SUBJKIT_TRACEBACK"):
            raise
        print(f"✘ {type(e).__name__}: {e}", file=sys.stderr)
        return 1
