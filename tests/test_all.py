# -*- coding: utf-8 -*-
"""完整回归：图示模板 + 公式 PDF + 裸符号检查。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from subjkit.check import scan  # noqa: E402
from subjkit.doc import build_pdf, read_css  # noqa: E402
from subjkit.md2html import build_html  # noqa: E402


def main() -> int:
    failures = 0

    print("[1/5] 图示模板")
    try:
        import tests.test_figures as figures  # noqa: PLC0415

        failures += figures.main()
    except Exception as e:  # noqa: BLE001
        failures += 1
        print(f"✘ 图示测试异常：{e}")

    print("\n[2/5] 裸符号检查")
    md = ROOT / "示例" / "公式对照.md"
    findings = scan(md.read_text(encoding="utf-8"))
    if len(findings) < 8:
        failures += 1
        print(f"✘ 检查器应能抓到样张里的错误写法，实际只抓到 {len(findings)} 处")
    else:
        print(f"✔ 抓到 {len(findings)} 处（样张故意保留了错误写法做对照）")

    print("\n[3/5] 公式 PDF")
    out = ROOT / "示例" / "输出" / "公式对照.pdf"
    try:
        result = build_pdf(md, out, preview=None)
        ok = result["pages"] >= 1 and result["formulas"] >= 20 and not result["math_errors"]
        print(("✔" if ok else "✘")
              + f" {result['pages']} 页，{result['formulas']} 条公式，"
                f"{len(result['math_errors'])} 条错误")
        if not ok:
            failures += 1
            for e in result["math_errors"][:5]:
                print(f"   - {e}")
    except Exception as e:  # noqa: BLE001
        failures += 1
        print(f"✘ 生成 PDF 失败：{e}")

    print("\n[4/5] 真实卷子（行内 HTML + 公式）")
    paper = ROOT / "示例" / "反例专项卷_重排.md"
    try:
        html, _ = build_html(paper.read_text(encoding="utf-8"), paper.parent, read_css(), {})
        if "<strong>" not in html or "&lt;strong&gt;" in html:
            failures += 1
            print("✘ 行内 <strong> 被转义成了文字")
        else:
            result = build_pdf(paper, ROOT / "示例" / "输出" / "反例专项卷_重排.pdf")
            if result["pages"] >= 2 and not result["math_errors"]:
                print(f"✔ {result['pages']} 页，{result['formulas']} 条公式，行内 HTML 正常")
            else:
                failures += 1
                print(f"✘ 重排卷异常：{result}")
    except Exception as e:  # noqa: BLE001
        failures += 1
        print(f"✘ 重排卷失败：{e}")

    print("\n[5/5] 实测问题回归（check 分级 / 图示校验 / 图例 / 刻度 / 表格分页）")
    try:
        import tests.test_regressions as regressions  # noqa: PLC0415

        failures += regressions.main()
    except Exception as e:  # noqa: BLE001
        failures += 1
        print(f"✘ 回归测试异常：{e}")

    print("\n" + ("✔ 全部通过" if failures == 0 else f"✘ {failures} 项失败"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
