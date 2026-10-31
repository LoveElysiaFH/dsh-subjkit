# -*- coding: utf-8 -*-
"""扫描讲义/试卷源文件里的「裸数学符号」。

这些符号如果直接写在正文里，浏览器只能回退到 Cambria Math / Segoe UI Symbol，
在宋体正文中会变成大小、基线都不对的替代字形——也就是学生看到的「符号打不出来」。

**但「数据」不是「公式」。** 学情报告里的 `274/450`（排名分母）、行文里的 `→`，
改成 `\\frac{274}{450}` 会把表格撑爆，属于误伤。所以这里分 profile：

- `paper`（默认）：出卷/讲义，一切「像公式但没包 $...$」的写法都是问题；
- `report`：数据报告，纯数字比值与行文箭头降级成 `info`，只提示、不算错。

每条结果带 `level`：`error`（必须改）/ `warn`（建议改）/ `info`（别改，只是告诉你这里有）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# 裸符号 → 建议的 LaTeX。只列真正会造成排版问题的，不追求穷尽。
SUGGEST = {
    "∈": r"\in", "∉": r"\notin", "⊆": r"\subseteq", "⊂": r"\subset",
    "⊇": r"\supseteq", "⊃": r"\supset", "∩": r"\cap", "∪": r"\cup",
    "∅": r"\varnothing", "≤": r"\le", "≥": r"\ge", "≠": r"\ne",
    "≈": r"\approx", "≡": r"\equiv", "∼": r"\sim", "≅": r"\cong",
    "√": r"\sqrt{…}", "∞": r"\infty", "∑": r"\sum", "∏": r"\prod",
    "∫": r"\int", "∂": r"\partial", "∇": r"\nabla", "±": r"\pm",
    "×": r"\times", "÷": r"\div", "°": r"^\circ",
    "′": "'", "″": "''", "⊥": r"\perp", "∥": r"\parallel",
    "∠": r"\angle", "△": r"\triangle", "⊙": r"\odot", "∽": r"\sim",
    "⇒": r"\Rightarrow", "⇔": r"\Leftrightarrow", "→": r"\to",
    "←": r"\leftarrow", "↔": r"\leftrightarrow", "∀": r"\forall",
    "∃": r"\exists", "∄": r"\nexists", "∴": r"\therefore", "∵": r"\because",
    "ℝ": r"\mathbb{R}", "ℕ": r"\mathbb{N}", "ℤ": r"\mathbb{Z}",
    "ℚ": r"\mathbb{Q}", "ℂ": r"\mathbb{C}", "ℓ": r"\ell",
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta",
    "ε": r"\varepsilon", "ζ": r"\zeta", "η": r"\eta", "θ": r"\theta",
    "ι": r"\iota", "κ": r"\kappa", "λ": r"\lambda", "μ": r"\mu",
    "ν": r"\nu", "ξ": r"\xi", "π": r"\pi", "ρ": r"\rho",
    "σ": r"\sigma", "τ": r"\tau", "υ": r"\upsilon", "φ": r"\varphi",
    "χ": r"\chi", "ψ": r"\psi", "ω": r"\omega",
    "Γ": r"\Gamma", "Δ": r"\Delta", "Θ": r"\Theta", "Λ": r"\Lambda",
    "Ξ": r"\Xi", "Π": r"\Pi", "Σ": r"\Sigma", "Υ": r"\Upsilon",
    "Φ": r"\Phi", "Ψ": r"\Psi", "Ω": r"\Omega",
    "²": "^{2}", "³": "^{3}", "¹": "^{1}", "⁰": "^{0}",
    "⁴": "^{4}", "⁵": "^{5}", "⁶": "^{6}", "⁷": "^{7}", "⁸": "^{8}", "⁹": "^{9}",
    "₀": "_{0}", "₁": "_{1}", "₂": "_{2}", "₃": "_{3}", "₄": "_{4}",
    "₅": "_{5}", "₆": "_{6}", "₇": "_{7}", "₈": "_{8}", "₉": "_{9}",
    "ₓ": "_{x}", "ₙ": "_{n}", "ₖ": "_{k}", "ₐ": "_{a}", "ₑ": "_{e}",
    "⁺": "^{+}", "⁻": "^{-}", "⁼": "^{=}",
}

# 这些符号在中文正文里很常见，但也可能是合法用法（如“×”表示乘号、°C），仍提示，交给会话判断。
WARN_ONLY = set("×÷·°′″→←↔")

PROFILES = {
    "paper": "出卷/讲义：一切像公式但没包 $...$ 的写法都要改",
    "report": "数据报告：纯数字比值与行文箭头只提示，不计为错误",
}

# 数字/数字：`274/450`、`405/600`。在 report 里是数据，在 paper 里也可能是数据（如“得分/满分”）。
RATIO_RE = re.compile(r"^(\d+)/(\d+)$")

MASK_PATTERNS = [
    re.compile(r"```.*?```", re.S),
    re.compile(r"`[^`\n]+`"),
    re.compile(r"\$\$.*?\$\$", re.S),
    re.compile(r"(?<!\\)\$[^$\n]+?\$"),
    re.compile(r"\\\(.*?\\\)", re.S),
    re.compile(r"!\[[^\]]*\]\([^)]*\)"),
    re.compile(r"https?://\S+"),
    re.compile(r"<[^>\n]*>"),          # HTML 标签本身不检查，只查标签之间的正文
]


def mask(text: str) -> str:
    """用等长空格替换代码/公式/链接，保留行号与列号。"""
    for pat in MASK_PATTERNS:
        text = pat.sub(lambda m: " " * len(m.group(0)), text)
    return text


# 除单个符号外，还要抓「写法」：a/b 与 x^2 同样会被排成不好看的样子。
DATE_RE = re.compile(r"\d{4}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{1,2}")
FRACTION_RE = re.compile(r"(?<![\w/])(\d+|[a-zA-Z])\s*/\s*(\d+|[a-zA-Z])(?![\w/])")
POWER_RE = re.compile(r"(?<![\\\w])([a-zA-Z])\s*\^\s*(\d+)(?![\w{])")


def _level(profile: str, kind: str, char: str, is_numeric_ratio: bool) -> str:
    """按 profile 给一条发现定级。paper 严、report 松，但都不会静默丢。"""
    if profile == "report":
        if kind == "分数" and is_numeric_ratio:
            return "info"      # 274/450 是数据
        if kind == "符号" and char in WARN_ONLY:
            return "info"      # 行文里的 → × ÷
        if kind == "幂":
            return "info"
        return "warn"
    # paper：出卷时这些都该改
    if kind == "符号":
        return "warn" if char in WARN_ONLY else "error"
    if kind == "分数":
        return "warn" if is_numeric_ratio else "error"
    return "warn"              # 幂


def scan(text: str, profile: str = "paper", exclude_ratios: bool = False) -> list[dict]:
    """扫描正文，返回带 `level` 的发现列表。

    Args:
        profile: `paper`（默认，严格）或 `report`（数据文档，宽松）。
        exclude_ratios: 直接丢掉「纯数字/纯数字」形态（`274/450`）。
    """
    if profile not in PROFILES:
        raise ValueError(f"未知 profile：{profile}（可用：{'、'.join(PROFILES)}）")

    masked = mask(text)
    src_lines = text.splitlines()
    findings = []
    for lineno, line in enumerate(masked.splitlines(), 1):
        hits = {}
        for col, ch in enumerate(line, 1):
            if ch in SUGGEST:
                hits.setdefault(ch, []).append(col)
        for ch, cols in hits.items():
            findings.append({
                "line": lineno,
                "col": cols[0],
                "char": ch,
                "count": len(cols),
                "suggest": SUGGEST[ch],
                "warning_only": ch in WARN_ONLY,
                "kind": "符号",
                "level": _level(profile, "符号", ch, False),
                "source": src_lines[lineno - 1].strip()[:120],
            })

        raw = src_lines[lineno - 1] if lineno - 1 < len(src_lines) else line
        dates = [m.span() for m in DATE_RE.finditer(raw)]
        for m in FRACTION_RE.finditer(line):
            if any(s <= m.start() < e for s, e in dates):
                continue
            a, b = m.group(1), m.group(2)
            numeric = bool(RATIO_RE.match(f"{a}/{b}"))
            if exclude_ratios and numeric:
                continue
            findings.append({
                "line": lineno,
                "col": m.start() + 1,
                "char": "/",
                "count": 1,
                "suggest": rf"\frac{{{a}}}{{{b}}}",
                "warning_only": True,
                "kind": "分数",
                "level": _level(profile, "分数", "/", numeric),
                "numeric_ratio": numeric,
                "source": raw.strip()[:120],
            })
        for m in POWER_RE.finditer(line):
            findings.append({
                "line": lineno,
                "col": m.start() + 1,
                "char": "^",
                "count": 1,
                "suggest": f"${m.group(1)}^{{{m.group(2)}}}$",
                "warning_only": True,
                "kind": "幂",
                "level": _level(profile, "幂", "^", False),
                "source": raw.strip()[:120],
            })
    findings.sort(key=lambda f: (f["line"], f["col"]))
    return findings


def counts(findings: list[dict]) -> dict:
    """按级别统计。`total` 是全部，`actionable` 是 error+warn。"""
    out = {"error": 0, "warn": 0, "info": 0}
    for f in findings:
        out[f.get("level", "error")] = out.get(f.get("level", "error"), 0) + 1
    out["total"] = len(findings)
    out["actionable"] = out["error"] + out["warn"]
    return out


def report(
    findings: list[dict],
    path: str | None = None,
    profile: str = "paper",
    max_rows: int = 200,
) -> str:
    c = counts(findings)
    if not findings:
        return "✔ 未发现裸数学符号：正文里的公式都应已包在 $...$ 或 $$...$$ 中。"

    head = (f"发现 {c['total']} 处（error {c['error']} / warn {c['warn']} / info {c['info']}）"
            + (f"　profile={profile}" if profile != "paper" else "")
            + (f"（{path}）" if path else "") + "：\n")

    # info 太多时只给数量，避免把有用的 error 淹掉
    show = findings
    folded = 0
    if profile == "report" and c["info"] > 20:
        show = [f for f in findings if f["level"] != "info"][:max_rows]
        folded = c["info"]
    else:
        show = findings[:max_rows]

    rows = ["  行:列    级别  类型  字符  写法"]
    for f in show:
        sugg = f["suggest"]
        if f["kind"] == "符号":
            sugg = f"${sugg}$"
        elif f["kind"] == "分数":
            sugg = f"$\\frac{{...}}{{...}}$（{sugg}）"
        rows.append(f"  {f['line']}:{f['col']:<4} {f.get('level', 'error'):<5} "
                    f"{f['kind']:<4} {f['char']:<4} {sugg}")

    tail = ""
    if len(findings) > len(show):
        tail += f"\n  …另有 {len(findings) - len(show)} 处未列出"
    if folded:
        tail += (f"\n  其中 {folded} 处是 info（数据比值 / 行文箭头），**不建议改成 LaTeX**："
                 "改成 \\frac 会把表格撑爆，改成 \\to 是噪音。")

    if c["error"] or (c["warn"] and profile == "paper"):
        guide = ("\n处理：符号连同整个式子包进 $...$；根号写成 $\\sqrt{b^2-4ac}$（花括号里写全，"
                 "上横线才会盖住整个被开方式）；分数写成 $\\frac{1}{2}$（分子在上、分母在下），不要用 1/2。")
    elif c["warn"]:
        guide = "\n处理：这次没有 error；warn 是建议项，可改可不改。"
    else:
        guide = "\n结论：只剩 info（数据/行文符号），这份文档不需要改。"
    return head + "\n".join(rows) + guide + tail


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    strict = "--strict" in argv
    profile = "paper"
    exclude_ratios = False
    rest: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--strict":
            pass
        elif a == "--exclude-ratios":
            exclude_ratios = True
        elif a == "--profile" and i + 1 < len(argv):
            i += 1
            profile = argv[i]
        elif a.startswith("--profile="):
            profile = a.split("=", 1)[1]
        else:
            rest.append(a)
        i += 1

    if not rest:
        print("用法：python subjkit.py check <文件.md> [--profile paper|report] "
              "[--exclude-ratios] [--strict]", file=sys.stderr)
        return 2
    p = Path(rest[0])
    text = sys.stdin.read() if str(p) == "-" else p.read_text(encoding="utf-8")
    findings = scan(text, profile=profile, exclude_ratios=exclude_ratios)
    print(report(findings, None if str(p) == "-" else str(p), profile=profile))
    if strict:
        # info 不算问题：report profile 下全是数据比值时不该让 CI 红
        return 1 if counts(findings)["actionable"] else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
