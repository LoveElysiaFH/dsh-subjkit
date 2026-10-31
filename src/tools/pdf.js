/**
 * tools/pdf.js — `subject_pdf`：Markdown → 打印用 PDF（公式是矢量）。
 *
 * 参数只有 CLI `pdf` 子命令的一层薄映射，没有额外业务逻辑：
 * 排版规则在 Python 里，改规则只改一处。
 */
import { callCli } from '../run.js';
import { sessionCwd } from '../cwd.js';

export function spec() {
  return {
    name: 'subject_pdf',
    description: [
      'Render a Markdown subject document to a print-ready A4 PDF whose formulas are vector paths —',
      'for math / physics / chemistry worksheets, handouts, answer keys and 学情 reports.',
      '',
      'Use it whenever a subject document has to be printed or handed to a student. Plain Unicode',
      '`√` and `1/2` cannot render a radical that covers its radicand or a stacked fraction; this',
      'pipeline turns every `$...$` formula into MathJax SVG, so the PDF does not depend on the',
      "reader's fonts.",
      '',
      'The source Markdown must already obey these rules — the PDF only renders what you wrote:',
      '- every formula inside `$...$` (inline) or `$$...$$` (display); never bare `√ ∈ ≤ π α ²`',
      '- radicals as `$\\sqrt{b^2-4ac}$` — the whole radicand inside the braces, or the bar stops short',
      '- fractions as `$\\frac{1}{2}$` (or `\\dfrac` when it must stay legible inline) — never `1/2`',
      '',
      'It runs subject_check (paper profile) itself and refuses to render while any error is left,',
      'so "check 不 0 不许出 PDF" is enforced rather than remembered. Pass `check: false` to skip.',
      'Use `check_only: true` to see the report without writing a file.',
      '',
      'Supports headings, lists, tables, blockquotes, images (paths relative to the .md), `**bold**`,',
      '`\\newpage` page breaks, and front matter (`title` / `subtitle` / `banner` / `footer` / `margin`).',
    ].join('\n'),
    parameters: {
      input: {
        type: 'string',
        required: true,
        description: 'Path to the source Markdown file. Relative paths resolve against the session '
          + 'working directory.',
      },
      output: {
        type: 'string',
        description: 'Where to write the PDF. Default: same directory and stem as the input, '
          + 'with a .pdf extension.',
      },
      split: {
        type: 'boolean',
        description: 'Also write `<name>_奇数页.pdf` and `<name>_偶数页.pdf` beside the PDF, for '
          + 'printers that only print one side at a time.',
      },
      preview: {
        type: 'boolean',
        description: 'Also render PNG preview(s) beside the PDF, e.g. `<name>_预览.png`. Use it to '
          + 'look at the rendered page instead of assuming the layout is right.',
      },
      preview_pages: {
        type: 'string',
        description: 'Only with preview: which pages to render, 1-based, as "1" or "1,3". '
          + 'Default: page 1.',
      },
      title: {
        type: 'string',
        description: 'Page title, overriding the front matter.',
      },
      subtitle: {
        type: 'string',
        description: 'Line under the title, overriding the front matter.',
      },
      footer: {
        type: 'string',
        description: 'Footer line such as 第 1 页 / 共 2 页, overriding the front matter.',
      },
      check: {
        type: 'boolean',
        description: 'Run subject_check (paper profile) first and refuse to render while any error '
          + 'remains — the "check 不 0 不许出 PDF" rule, enforced by the tool rather than remembered. '
          + 'Default true. Set false only when you deliberately keep a bare symbol.',
      },
      check_only: {
        type: 'boolean',
        description: 'Only run the check and report; do not write a PDF.',
      },
    },
    output: {
      // 宿主的 output.schema 不是标准 JSON Schema，而是「value schema DSL」：
      // 必填写在属性上（required: true），对象级的 required 数组会被直接拒掉。
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          text: {
            type: 'string',
            required: true,
            description: 'Page and formula counts, the written paths, and any TeX that failed to '
              + 'typeset (with the source line to fix).',
          },
        },
      },
      render(args, value) {
        return [{ type: 'text', text: value.text }];
      },
    },
    timeoutMs: 300_000,
    isConcurrencySafe() {
      return true;
    },
  };
}

export async function execute(args, exec, ctx) {
  const input = String(args?.input ?? '').trim();
  if (!input) throw new Error('input 是必填项：给出 .md 源文件路径');

  const cwd = await sessionCwd(ctx, exec);
  const data = await callCli('pdf', { args: cliArgs({ ...args, input }), cwd });
  return { text: describe(data) };
}

function cliArgs(args) {
  // 注意：`pdf` 这个子命令名由 callCli 加，这里只给参数。
  const argv = [args.input];
  if (args.output) argv.push('-o', String(args.output));
  if (args.title) argv.push('--title', String(args.title));
  if (args.subtitle) argv.push('--subtitle', String(args.subtitle));
  if (args.footer) argv.push('--footer', String(args.footer));
  if (args.split) argv.push('--split');
  if (args.check === false) argv.push('--no-check');
  if (args.check_only) argv.push('--check-only');
  if (args.preview) {
    // 显式给 __auto__：`--preview` 是 nargs='?'，显式传值比依赖「后面跟的是 flag」更稳。
    argv.push('--preview', '__auto__');
    if (args.preview_pages) argv.push('--preview-pages', String(args.preview_pages));
  }
  return argv;
}

function describe(data) {
  const lines = [`PDF：${data.pdf}`, `${data.pages} 页，${data.formulas} 条公式`];
  if (data.odd) {
    lines.push(`奇数页：${data.odd}`, `偶数页：${data.even}`);
  }
  for (const p of data.previews ?? []) lines.push(`预览：${p}`);
  if (data.check && data.check.warn) {
    lines.push(`（出图前 check 另有 ${data.check.warn} 处 warn，未拦截）`);
  }

  const errors = data.math_errors ?? [];
  if (errors.length) {
    lines.push('', `⚠ ${errors.length} 条公式没排好（TeX 写错，后面是原文）：`);
    for (const e of errors.slice(0, 10)) lines.push(`  - ${e?.message ?? e}　<< ${e?.tex ?? ''}`);
    if (errors.length > 10) lines.push(`  …另有 ${errors.length - 10} 条`);
  } else if (data.formulas > 0) {
    lines.push('公式全部排版成功。');
  }
  return lines.join('\n');
}
