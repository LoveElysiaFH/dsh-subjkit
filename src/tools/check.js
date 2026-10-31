/**
 * tools/check.js — `subject_check`：找出正文里「用字符代替 TeX」的地方。
 *
 * 只读、很快，是写文档时反复跑的那一步：check 到 0 处，再 subject_pdf。
 * 报告原文由 Python 生成（带行:列和建议写法），这里不再二次加工。
 */
import { callCli } from '../run.js';
import { sessionCwd } from '../cwd.js';

export function spec() {
  return {
    name: 'subject_check',
    description: [
      'Scan a Markdown or HTML document for math written as plain characters instead of TeX, and',
      'report every hit as 行:列 with the TeX to use instead. Each hit is graded error / warn / info.',
      '',
      'It catches three shapes:',
      '- bare symbols — `√ ∈ ∩ ≤ ≠ ∅ π α ⊥ ∠ ² ₀ ∞ ∑` … (they fall back to a substitute glyph in 宋体)',
      '- slash fractions — `1/2`, `1/a` (should be `$\\frac{1}{2}$`)',
      '- caret powers outside math — `x^2` (should be `$x^{2}$`)',
      '',
      'Pick the profile by what the document IS, because a ratio is not a formula:',
      '- profile "paper" (default): worksheets, handouts, answer keys. Everything that looks like',
      '  math but is not inside $...$ is an error — fix to 0 before subject_pdf.',
      '- profile "report": data reports and 学情报告. `274/450` ranked ratios and prose arrows',
      '  (`→`, `≈`) degrade to info: they are data, and converting them to \\frac would blow up a',
      '  six-column table. Errors-only blocking then passes untouched.',
      'Run it after drafting and before subject_pdf. Code blocks, inline code, existing $...$ / $$...$$',
      'and HTML tags are skipped, so a correct file stays silent.',
    ].join('\n'),
    parameters: {
      input: {
        type: 'string',
        required: true,
        description: 'Path to the .md or .html file to scan. Relative paths resolve against the '
          + 'session working directory.',
      },
      profile: {
        type: 'string',
        enum: ['paper', 'report'],
        description: 'paper = 出卷/讲义（默认，严格）；report = 数据报告（比值与行文箭头降级为 info）。'
          + '拿不准时问一句：这份文档里的 `1/2` 会被印成公式吗？不会就用 report。',
      },
      exclude_ratios: {
        type: 'boolean',
        description: 'Drop plain number/number hits (`274/450`) entirely instead of grading them. '
          + 'Use when even the info list is noise.',
      },
    },
    output: {
      // 必填写在属性上（required: true）：宿主用的是 value schema DSL，不是 JSON Schema。
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          text: {
            type: 'string',
            required: true,
            description: 'Counts by level (error / warn / info), one line per finding with 行:列, '
              + 'the kind, the character and the suggested TeX, then how to proceed.',
          },
        },
      },
      render(args, value) {
        return [{ type: 'text', text: value.text }];
      },
    },
    timeoutMs: 60_000,
    isConcurrencySafe() {
      return true;
    },
  };
}

export async function execute(args, exec, ctx) {
  const input = String(args?.input ?? '').trim();
  if (!input) throw new Error('input 是必填项：给出要检查的 .md / .html 路径');

  const profile = args?.profile === 'report' ? 'report' : 'paper';
  const argv = [input, '--profile', profile];
  if (args?.exclude_ratios) argv.push('--exclude-ratios');

  const cwd = await sessionCwd(ctx, exec);
  const data = await callCli('check', { args: argv, cwd, timeoutMs: 45_000 });
  return { text: describe(data) };
}

function describe(data) {
  // Python 的 report() 已经带了分级统计和怎么改，这里只补截断提示。
  const report = data.report ?? `共 ${data.count} 处。`;
  return data.truncated > 0
    ? `${report}\n（另有 ${data.truncated} 处未列出；先改上面这些，再重新检查。）`
    : report;
}
