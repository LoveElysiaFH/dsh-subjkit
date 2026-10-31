/**
 * tools/figure.js — `subject_figure`：按 spec 画一张学科图示（SVG/PNG）。
 *
 * spec 是一个自由形状的对象（模板不同字段不同），所以这里只校验「必须有 type」，
 * 其余交给 Python 的模板函数报错——报错信息本来就写得比这里清楚。
 */
import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { callCli } from '../run.js';
import { sessionCwd } from '../cwd.js';

const DEFAULT_OUTPUT = 'figure.svg';
const DEFAULT_DPI = 300;

export function spec() {
  return {
    name: 'subject_figure',
    description: [
      'Draw one subject diagram as a vector file, for worksheets, handouts and answer keys.',
      '',
      '`type` selects the template:',
      '  circuit     电路：nodes {name:[x,y]} + elements {kind,from,to}'
      + ' (battery/resistor/lamp/switch/ammeter/voltmeter/capacitor/rheostat/fuse/motor)',
      '  force       受力分析：body + forces {angle,magnitude,label}; angle 0° right, 90° up',
      '  incline     斜面：angle, decompose (draw mg split into components)',
      '  optics      凸透镜成像：focal, object_distance, object_height',
      '  plot        函数图像：functions {expr} — `^` for powers, sin/cos/sqrt/log/abs',
      '  geometry    平面几何：points, segments, polygons, circles, angles, right_angles, ticks',
      '  numberline  数轴：min, max, points, intervals',
      '  venn        韦恩图：sets, counts',
      '  apparatus   化学装置：parts'
      + ' (beaker/flask/round_flask/test_tube/gas_jar/trough/funnel/alcohol_lamp/iron_stand/condenser/thermometer)',
      '  molecule    分子结构式：smiles',
      '  cell        细胞：kind=plant|animal, notes',
      '  flow        流程框图：steps, layout=horizontal|vertical',
      '  grid        田字格/米字格：chars, pinyin, cols',
      '',
      'Coordinates are y-up in arbitrary units. Math labels go inside `$...$`, e.g. `"$mg\\sin\\theta$"`;',
      'keep Chinese out of a formula string (use two labels instead).',
      '',
      'Field-by-field documentation for every template is in the subject-diagram skill. Output `.svg`',
      'for print (subject_pdf embeds it), `.png` for showing the result.',
    ].join('\n'),
    parameters: {
      spec: {
        type: 'object',
        additionalProperties: true,
        description: 'The figure description: `{ "type": "incline", "angle": 30, "decompose": true }`. '
          + '`type` is required; other fields depend on the template.',
      },
      output: {
        type: 'string',
        description: `Output file; the extension picks the format (.svg vector, .png raster). Default: ${DEFAULT_OUTPUT}.`,
      },
      dpi: {
        type: 'integer',
        description: `PNG resolution, 72-600. Default ${DEFAULT_DPI}; ignored for .svg.`,
      },
      dry_run: {
        type: 'boolean',
        description: 'Validate the spec and return what it would draw, without writing a file. '
          + 'For `cell` it also returns the built-in label coordinates, so you can pick a free spot '
          + 'for your own notes instead of guessing.',
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
            description: 'Absolute path of the written file plus its template and size.',
          },
        },
      },
      render(args, value) {
        return [{ type: 'text', text: value.text }];
      },
    },
    timeoutMs: 150_000,
    isConcurrencySafe() {
      return true;
    },
  };
}

export async function execute(args, exec, ctx) {
  const figure = normalizeSpec(args?.spec);
  const output = String(args?.output ?? '').trim() || DEFAULT_OUTPUT;
  const dryRun = args?.dry_run === true;
  const dpi = clampDpi(args?.dpi);
  const cwd = await sessionCwd(ctx, exec);

  const data = await callCli('fig', {
    prepare: (dir) => writeFile(join(dir, 'spec.json'), JSON.stringify(figure), 'utf8'),
    // 子命令名 `fig` 由 callCli 加，这里只给参数。
    args: (dir) => [
      '--spec', join(dir, 'spec.json'), '-o', output, '--dpi', String(dpi),
      ...(dryRun ? ['--dry-run'] : []),
    ],
    cwd,
    timeoutMs: dryRun ? 30_000 : 120_000,
  });
  return { text: describe(data) };
}

function normalizeSpec(raw) {
  if (raw == null) throw new Error('spec 是必填项：给出带 type 的图示参数，例如 {"type":"incline","angle":30}');
  let value = raw;
  if (typeof value === 'string') {
    try {
      value = JSON.parse(value);
    } catch (e) {
      throw new Error(`spec 不是合法 JSON：${e.message}`);
    }
  }
  if (typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('spec 必须是对象，例如 {"type":"incline","angle":30}');
  }
  if (typeof value.type !== 'string' || !value.type) {
    throw new Error('spec.type 是必填项：circuit / force / incline / optics / plot / geometry / '
      + 'numberline / venn / apparatus / molecule / cell / flow / grid');
  }
  return value;
}

function clampDpi(raw) {
  const n = Number(raw);
  if (!Number.isFinite(n)) return DEFAULT_DPI;
  return Math.min(600, Math.max(72, Math.round(n)));
}

function describe(data) {
  if (data.dry_run) {
    const lines = [`✔ spec 校验通过：${data.template}（dry-run，未出图）`, `将写入：${data.would_write}`];
    for (const w of data.warnings ?? []) lines.push(`· ${w}`);
    for (const item of data.info?.builtin_labels ?? []) {
      lines.push(`内置标签：${item.text} at=[${item.at.join(', ')}]`);
    }
    return lines.join('\n');
  }
  const kb = typeof data.bytes === 'number' ? `，${(data.bytes / 1024).toFixed(1)} KB` : '';
  const lines = [`图示：${data.out}`, `类型：${data.type}（${data.format}${kb}）`];
  for (const w of data.warnings ?? []) lines.push(`· ${w}`);
  return lines.join('\n');
}
