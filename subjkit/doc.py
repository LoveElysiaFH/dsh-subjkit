# -*- coding: utf-8 -*-
"""Markdown → HTML → MathJax 矢量公式 → Edge 无头打印 PDF。"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from .md2html import build_html

TOOL_DIR = Path(__file__).resolve().parent.parent
ASSETS = TOOL_DIR / "assets"
RENDER_MJS = ASSETS / "render_math.mjs"
BASE_CSS = ASSETS / "base.css"

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
]

PDF_ARGS = [
    "--headless=new",
    "--disable-gpu",
    "--no-pdf-header-footer",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--hide-scrollbars",
    "--run-all-compositor-stages-before-draw",
    "--virtual-time-budget=20000",
]


def node_exe() -> str:
    for cand in (shutil.which("node"), r"C:\Program Files\nodejs\node.exe"):
        if cand and Path(cand).exists():
            return cand
    raise RuntimeError("找不到 node.exe；请确认 Node.js 已安装")


def edge_exe() -> str:
    for cand in EDGE_CANDIDATES:
        if cand and Path(cand).exists():
            return cand
    raise RuntimeError("找不到 Microsoft Edge；可用 --html 只生成 HTML，或安装 Edge")


def read_css() -> str:
    return BASE_CSS.read_text(encoding="utf-8")


def render_math_html(html_in: Path, html_out: Path) -> dict:
    cmd = [node_exe(), str(RENDER_MJS), "--html", str(html_in), "--out", str(html_out)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=180)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("MathJax 渲染超时（180 秒）") from e
    report = {}
    for line in reversed((proc.stdout or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                report = json.loads(line)
                break
            except json.JSONDecodeError:
                pass
    if proc.returncode != 0 and not report:
        raise RuntimeError(f"MathJax 渲染失败：{proc.stderr[-800:] or proc.stdout[-800:]}")
    if report.get("fatal"):
        raise RuntimeError(f"MathJax 渲染失败：{report['fatal']}")
    return report


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    work = Path(tempfile.mkdtemp(prefix="kt_edge_"))
    try:
        cmd = [edge_exe(), *PDF_ARGS, f"--user-data-dir={work / 'profile'}",
               f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=180)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("Edge 打印超时（180 秒）") from e
        if not pdf_path.exists() or pdf_path.stat().st_size < 1024:
            raise RuntimeError(f"Edge 未生成 PDF（exit={proc.returncode}）：{proc.stderr[-600:]}")
        if not pdf_path.read_bytes().startswith(b"%PDF"):
            raise RuntimeError("Edge 输出不是有效 PDF")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def pdf_pages(pdf_path: Path) -> int:
    from pypdf import PdfReader
    return len(PdfReader(str(pdf_path)).pages)


def split_odd_even(pdf_path: Path) -> tuple[Path, Path]:
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(str(pdf_path))
    odd, even = PdfWriter(), PdfWriter()
    for i, page in enumerate(reader.pages):
        (odd if i % 2 == 0 else even).add_page(page)
    stem = pdf_path.with_suffix("")
    odd_path = stem.parent / (stem.name + "_奇数页.pdf")
    even_path = stem.parent / (stem.name + "_偶数页.pdf")
    with open(odd_path, "wb") as fh:
        odd.write(fh)
    with open(even_path, "wb") as fh:
        even.write(fh)
    return odd_path, even_path


def render_preview(pdf_path: Path, png_path: Path, pages: list[int] | None = None, zoom: float = 2.0) -> list[Path]:
    import pymupdf
    doc = pymupdf.open(str(pdf_path))
    idxs = [p - 1 for p in pages] if pages else list(range(len(doc)))
    outs = []
    for k, idx in enumerate(idxs):
        if idx < 0 or idx >= len(doc):
            continue
        pix = doc[idx].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        target = png_path if len(idxs) == 1 else png_path.with_name(f"{png_path.stem}_p{idx + 1}{png_path.suffix}")
        pix.save(str(target))
        outs.append(target)
    doc.close()
    return outs


def build_pdf(
    md_path: str | Path,
    out_pdf: str | Path,
    meta: dict | None = None,
    keep_html: bool = False,
    split: bool = False,
    preview: str | Path | None = None,
    preview_pages: list[int] | None = None,
) -> dict:
    md_path = Path(md_path).resolve()
    if not md_path.exists():
        raise FileNotFoundError(md_path)
    out_pdf = Path(out_pdf).resolve()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    md_text = md_path.read_text(encoding="utf-8")
    html_doc, merged_meta = build_html(md_text, md_path.parent, read_css(), meta)

    work = Path(tempfile.mkdtemp(prefix=f"kt_{uuid.uuid4().hex[:8]}_"))
    try:
        raw_html = work / "raw.html"
        ren_html = work / "rendered.html"
        raw_html.write_text(html_doc, encoding="utf-8")
        report = render_math_html(raw_html, ren_html)
        if keep_html:
            html_out = out_pdf.with_suffix(".html")
            shutil.copyfile(ren_html, html_out)
        html_to_pdf(ren_html, out_pdf)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    result = {
        "pdf": str(out_pdf),
        "pages": pdf_pages(out_pdf),
        "formulas": report.get("formulas", 0),
        "math_errors": report.get("errors", []),
        "title": merged_meta.get("title", ""),
    }
    if split:
        odd, even = split_odd_even(out_pdf)
        result["odd"] = str(odd)
        result["even"] = str(even)
    if preview:
        preview = Path(preview).resolve()
        preview.parent.mkdir(parents=True, exist_ok=True)
        result["previews"] = [str(p) for p in render_preview(out_pdf, preview, preview_pages)]
    return result
