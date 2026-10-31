# -*- coding: utf-8 -*-
"""把示例图示拼成一张检查用的 PDF（两栏）。"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from subjkit.doc import html_to_pdf  # noqa: E402

OUT = ROOT / "示例" / "输出" / "图示"
OUT.mkdir(parents=True, exist_ok=True)
files = sorted(f for f in OUT.glob("*.svg") if not f.name.startswith("_"))
cards = []
for f in files:
    data = base64.b64encode(f.read_bytes()).decode("ascii")
    cards.append(
        f'<div class="card"><img src="data:image/svg+xml;base64,{data}">'
        f'<div class="cap">{f.stem}</div></div>'
    )

html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<style>
@page {{ size: A4; margin: 10mm; }}
body {{ font-family: "SimSun","Microsoft YaHei",sans-serif; margin: 0; }}
h1 {{ font-size: 15pt; text-align: center; font-family: "SimHei"; margin: 0 0 4mm; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 5mm 5mm; }}
.card {{ border: 1px solid #bbb; padding: 2mm; text-align: center; break-inside: avoid; }}
.card img {{ width: 100%; height: 68mm; object-fit: contain; }}
.cap {{ font-size: 9pt; color: #333; margin-top: 1mm; }}
</style></head><body>
<h1>学科工具 · 图示模板自检</h1>
<div class="grid">{''.join(cards)}</div>
</body></html>"""

src = OUT / "_gallery.html"
src.write_text(html, encoding="utf-8")
pdf = OUT / "_gallery.pdf"
html_to_pdf(src, pdf)
print(pdf)
