# -*- coding: utf-8 -*-
"""轻量 Markdown → 打印用 HTML。

只实现学科资料真正用得到的语法，换取「零依赖 + 可控排版」：
标题、段落、列表、表格、引用、代码、图片、分页，以及 $...$ / $$...$$ 公式占位。
公式不在这里渲染，交给 assets/render_math.mjs（MathJax → 矢量 SVG）。
"""
from __future__ import annotations

import base64
import html
import re
from pathlib import Path

CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]")
MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp",
}

# 正文里允许保留的行内 HTML（只放行排版类标签，避免把整段 HTML 当 Markdown 转义）
INLINE_TAG = re.compile(
    r"</?(?:strong|b|em|i|u|s|del|br|span|sup|sub|mark)(?:\s+[^<>]*)?>", re.I
)


def _is_cjk(ch: str) -> bool:
    return bool(ch and CJK.match(ch))


def join_lines(lines: list[str]) -> str:
    """中文行之间不插空格，英文行之间插一个空格。"""
    out = ""
    for raw in lines:
        line = raw.rstrip()
        hard_break = line.endswith("  ")
        line = line.strip()
        if not line:
            continue
        if not out:
            out = line
        elif hard_break:
            out += "<br>" + line
        elif _is_cjk(out[-1]) and _is_cjk(line[0]):
            out += line
        elif out.endswith(">") or line.startswith("<"):
            out += line
        else:
            out += " " + line
    return out


def _math_span(tex: str, display: bool = False) -> str:
    b64 = base64.b64encode(tex.encode("utf-8")).decode("ascii")
    if display:
        return f'<div class="math-display" data-tex-b64="{b64}"></div>'
    return f'<span class="math-inline" data-tex-b64="{b64}"></span>'


def _embed_image(src: str, base_dir: Path, alt: str) -> str:
    src = src.strip()
    if re.match(r"^(https?:|data:)", src, re.I):
        return f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(alt)}">'
    p = Path(src)
    if not p.is_absolute():
        p = (base_dir / src).resolve()
    if p.exists() and p.suffix.lower() in MIME:
        if p.stat().st_size > 30 * 1024 * 1024:
            raise ValueError(f"图片过大（>30MB）：{p}")
        data = base64.b64encode(p.read_bytes()).decode("ascii")
        return (f'<img src="data:{MIME[p.suffix.lower()]};base64,{data}" '
                f'alt="{html.escape(alt)}">')
    return f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(alt)}" class="missing">'


def inline(text: str, base_dir: Path) -> str:
    """行内语法；公式先换成占位符，避免被 HTML 转义或强调语法破坏。"""
    stash: list[str] = []

    def keep(fragment: str) -> str:
        stash.append(fragment)
        return f"\x02S{len(stash) - 1}\x03"

    # 行内代码
    text = re.sub(r"`([^`]+)`", lambda m: keep("<code>" + html.escape(m.group(1)) + "</code>"), text)

    # 公式：$...$ 与 \(...\)
    def math_repl(m: re.Match) -> str:
        return keep(_math_span(m.group(1).strip(), False))

    text = re.sub(r"(?<!\\)\$(?!\s)((?:\\.|[^$\\])+?)(?<!\s)\$", math_repl, text)
    text = re.sub(r"\\\((.+?)\\\)", math_repl, text, flags=re.S)

    # 图片先于链接
    def img_repl(m: re.Match) -> str:
        return keep(_embed_image(m.group(2), base_dir, m.group(1)))

    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", img_repl, text)

    # 允许正文里少量行内 HTML（试卷常用 <strong>/<span>/<br>），不要把它们转义成文字
    text = re.sub(INLINE_TAG, lambda m: keep(m.group(0)), text)

    text = html.escape(text, quote=False)

    # 链接
    text = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>',
        text,
    )
    # 强调
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)

    for i, fragment in enumerate(stash):
        text = text.replace(f"\x02S{i}\x03", fragment)
    return text


def _table(lines: list[str], start: int, base_dir: Path) -> tuple[str, int]:
    header = [c.strip() for c in lines[start].strip().strip("|").split("|")]
    aligns = []
    for c in lines[start + 1].strip().strip("|").split("|"):
        c = c.strip()
        if c.startswith(":") and c.endswith(":"):
            aligns.append("center")
        elif c.endswith(":"):
            aligns.append("right")
        else:
            aligns.append("left")
    rows = []
    i = start + 2
    while i < len(lines) and "|" in lines[i] and lines[i].strip():
        rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
        i += 1

    def cell(tag: str, text: str, idx: int) -> str:
        align = aligns[idx] if idx < len(aligns) else "center"
        return f'<{tag} style="text-align:{align}">{inline(text, base_dir)}</{tag}>'

    out = ["<table><thead><tr>"]
    out += [cell("th", c, k) for k, c in enumerate(header)]
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        out += [cell("td", c, k) for k, c in enumerate(row)]
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out), i


def md_to_html(text: str, base_dir: Path) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    para: list[str] = []
    i = 0
    pending_keep = False

    def push(block: str) -> None:
        """加一个块级元素；前面若有 <!--keep-->，就套上 .keep（整块不跨页）。"""
        nonlocal pending_keep
        out.append(f'<div class="keep">{block}</div>' if pending_keep else block)
        pending_keep = False

    def flush() -> None:
        if para:
            body = join_lines(para)
            if body:
                push(f"<p>{inline(body, base_dir)}</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()

        # 围栏代码
        if s.startswith("```"):
            flush()
            lang = s[3:].strip()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            cls = f' class="language-{html.escape(lang)}"' if lang else ""
            push(f"<pre><code{cls}>{html.escape(chr(10).join(buf))}</code></pre>")
            continue

        # 独立成段的公式 $$
        if s.startswith("$$"):
            flush()
            if s.endswith("$$") and len(s) > 4:
                tex = s[2:-2].strip()
                i += 1
            else:
                buf = [s[2:]]
                i += 1
                while i < len(lines) and "$$" not in lines[i]:
                    buf.append(lines[i])
                    i += 1
                if i < len(lines):
                    buf.append(lines[i].split("$$")[0])
                    i += 1
                tex = "\n".join(buf).strip()
            push(_math_span(tex, True))
            continue

        # 整块不跨页标记：下一块（表格/图/公式）套上 .keep
        if s in {"<!--keep-->", "<!-- keep -->"}:
            flush()
            pending_keep = True
            i += 1
            continue

        # 分页
        if s in {r"\newpage", r"\pagebreak", "<!-- pagebreak -->", "<!--pagebreak-->"}:
            flush()
            out.append('<div class="pagebreak"></div>')
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush()
            level = len(m.group(1))
            push(f"<h{level}>{inline(m.group(2).strip(), base_dir)}</h{level}>")
            i += 1
            continue

        # 分隔线
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", s):
            flush()
            push("<hr>")
            i += 1
            continue

        # 表格
        if "|" in s and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$", lines[i + 1]):
            flush()
            table_html, i = _table(lines, i, base_dir)
            push(table_html)
            continue

        # 引用
        if s.startswith(">"):
            flush()
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].lstrip())
                i += 1
            body = join_lines(buf)
            push(f"<blockquote><p>{inline(body, base_dir)}</p></blockquote>")
            continue

        # 列表（同类型连续项）
        m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
        if m:
            flush()
            ordered = m.group(2)[0].isdigit()
            tag = "ol" if ordered else "ul"
            items: list[str] = [f"<{tag}>"]
            while i < len(lines):
                mm = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", lines[i])
                if not mm or mm.group(2)[0].isdigit() != ordered:
                    break
                items.append(f"<li>{inline(mm.group(3).strip(), base_dir)}</li>")
                i += 1
            items.append(f"</{tag}>")
            push("".join(items))
            continue

        # 原样 HTML（便于试卷里的作答框、表格等）
        if s.startswith("<") and s.endswith(">"):
            flush()
            push(line)
            i += 1
            continue

        # 空行收段
        if not s:
            flush()
            i += 1
            continue

        para.append(line)
        i += 1

    flush()
    return "\n".join(out)


def parse_front_matter(text: str) -> tuple[dict, str]:
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        meta[k.strip()] = v
    return meta, m.group(2)


def build_html(md_text: str, base_dir: Path, css: str, cli_meta: dict | None = None) -> tuple[str, dict]:
    meta, body_md = parse_front_matter(md_text)
    if cli_meta:
        meta.update({k: v for k, v in cli_meta.items() if v not in (None, "")})
    body = md_to_html(body_md, base_dir)

    title = meta.get("title", "")
    subtitle = meta.get("subtitle", "")
    banner = meta.get("banner", "")
    footer = meta.get("footer", "")
    margin = meta.get("margin", "")
    fontsize = meta.get("fontsize", "")

    head_parts = []
    if banner:
        head_parts.append(f'<div class="banner">{inline(banner, base_dir)}</div>')
    if title:
        head_parts.append(f"<h1>{inline(title, base_dir)}</h1>")
    if subtitle:
        head_parts.append(f'<div class="sub">{inline(subtitle, base_dir)}</div>')

    extra_css = ""
    if margin:
        extra_css += f"@page {{ margin: {margin}; }}\n"
    if fontsize:
        extra_css += f"body {{ font-size: {fontsize}; }}\n"
    if meta.get("css"):
        css_path = Path(meta["css"])
        if not css_path.is_absolute():
            css_path = base_dir / css_path
        if css_path.exists():
            extra_css += css_path.read_text(encoding="utf-8") + "\n"

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{html.escape(title or '学科资料')}</title>
<style>
{css}
{extra_css}
</style>
</head>
<body>
{chr(10).join(head_parts)}
{body}
{f'<div class="foot">{inline(footer, base_dir)}</div>' if footer else ''}
</body>
</html>"""
    return doc, meta
