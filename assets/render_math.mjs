/**
 * render_math.mjs —— 把 HTML 里的公式占位符换成 MathJax 矢量 SVG，或直接渲染单条公式。
 *
 * 两种用法：
 *   node render_math.mjs --html in.html --out out.html
 *   node render_math.mjs --tex "x=\frac{1}{2}" --display --out f.svg
 *
 * 设计要点：
 *  - 公式以 base64 放在 data-tex-b64 里，避免 HTML 属性转义把反斜杠/引号弄坏；
 *  - 输出 SVG 用 fontCache:"local"，每个公式自带 <defs>，脱离网络和字体文件也能打印；
 *  - 渲染失败不抛异常，换成红色「公式错误」占位并在 JSON 报告里给出 TeX，方便会话修。
 */
import fs from 'node:fs';
import path from 'node:path';
import { mathjax } from 'mathjax-full/js/mathjax.js';
import { TeX } from 'mathjax-full/js/input/tex.js';
import { SVG } from 'mathjax-full/js/output/svg.js';
import { liteAdaptor } from 'mathjax-full/js/adaptors/liteAdaptor.js';
import { RegisterHTMLHandler } from 'mathjax-full/js/handlers/html.js';
import { AllPackages } from 'mathjax-full/js/input/tex/AllPackages.js';

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const texInput = new TeX({ packages: AllPackages, processEscapes: true });
const svgOutput = new SVG({ fontCache: 'local' });
const doc = mathjax.document('', { InputJax: texInput, OutputJax: svgOutput });

const cache = new Map();
const errors = [];
let count = 0;

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderOne(tex, display) {
  const key = (display ? 'D:' : 'I:') + tex;
  if (cache.has(key)) return cache.get(key);
  let html;
  try {
    const node = doc.convert(tex, { display: Boolean(display) });
    html = adaptor.outerHTML(node);
    if (/<merror|data-mjx-error/.test(html)) {
      const msg = (html.match(/data-mjx-error="([^"]*)"/) || [])[1] || 'TeX 语法错误';
      errors.push({ tex, message: msg.replace(/&quot;/g, '"').replace(/&amp;/g, '&') });
    }
  } catch (e) {
    errors.push({ tex, message: String(e && e.message ? e.message : e) });
    html = `<span class="math-error" title="${esc(String(e))}">[公式错误：${esc(tex)}]</span>`;
  }
  cache.set(key, html);
  count += 1;
  return html;
}

function decode(b64) {
  return Buffer.from(b64, 'base64').toString('utf8');
}

function renderHtml(inputPath, outputPath) {
  let html = fs.readFileSync(inputPath, 'utf8');
  const re = /<(span|div) class="math-(inline|display)" data-tex-b64="([^"]*)"><\/\1>/g;
  html = html.replace(re, (m, tag, kind, b64) => renderOne(decode(b64), kind === 'display'));
  fs.writeFileSync(outputPath, html, 'utf8');
}

function renderFormula(tex, display, outPath) {
  const wrapped = renderOne(tex, display);
  if (/class="math-error"/.test(wrapped)) {
    throw new Error('公式渲染失败：' + tex);
  }
  const m = wrapped.match(/<svg[\s\S]*<\/svg>/);
  if (!m) throw new Error('MathJax 未返回 SVG');
  let svg = m[0];
  // 单条公式给一个明确尺寸，便于 <img> 使用；保留 viewBox 以便缩放。
  const vb = svg.match(/viewBox="([^"]+)"/);
  const h = svg.match(/height="([\d.]+)ex"/);
  const w = svg.match(/width="([\d.]+)ex"/);
  if (vb && h && w) {
    const px = 16; // 1ex ≈ 8px 时接近正文；这里按 16px/ex 给出可读尺寸
    svg = svg.replace(/height="[\d.]+ex"/, `height="${(parseFloat(h[1]) * px).toFixed(1)}"`)
             .replace(/width="[\d.]+ex"/, `width="${(parseFloat(w[1]) * px).toFixed(1)}"`);
  }
  svg = svg.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ');
  fs.mkdirSync(path.dirname(path.resolve(outPath)), { recursive: true });
  fs.writeFileSync(outPath, svg, 'utf8');
}

function main() {
  const args = process.argv.slice(2);
  const get = (name) => {
    const i = args.indexOf(name);
    return i >= 0 ? args[i + 1] : undefined;
  };
  const has = (name) => args.includes(name);

  if (has('--html')) {
    const input = get('--html');
    const output = get('--out');
    if (!input || !output) throw new Error('需要 --html 和 --out');
    renderHtml(input, output);
    process.stdout.write(JSON.stringify({ ok: errors.length === 0, formulas: count, errors }) + '\n');
    return;
  }

  if (has('--tex')) {
    const tex = get('--tex');
    const out = get('--out');
    if (!tex || !out) throw new Error('需要 --tex 和 --out');
    renderFormula(tex, has('--display'), out);
    process.stdout.write(JSON.stringify({ ok: true, formulas: 1, errors }) + '\n');
    return;
  }

  throw new Error('用法：--html <in> --out <out> 或 --tex <tex> --out <svg> [--display]');
}

try {
  main();
} catch (e) {
  process.stdout.write(JSON.stringify({ ok: false, formulas: count, errors, fatal: String(e && e.message ? e.message : e) }) + '\n');
  process.exit(2);
}
