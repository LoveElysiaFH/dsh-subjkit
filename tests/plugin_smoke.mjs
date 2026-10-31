/*
 * 插件层的静态 + 端到端验证（不需要启动 DSH）。
 *
 * 跑法：
 *     node tests/plugin_smoke.mjs
 *
 * 三件事：
 * 1. **schema 审计**：每个工具声明的参数，必须和它的 execute 真正读的参数一一对应
 *    —— 宿主管参数是「按 schema 过滤」，两边不一致不会报错，只会静默丢参数；
 * 2. **注册**：用一个 defineTool 桩 + mock ctx 跑 apply()，确认注册 3 个工具、2 个技能，
 *    dispose 能全部解绑；并且注册失败时 apply 不抛异常；
 * 3. **真跑**：三个工具都真的调用 Python CLI，出 PDF / SVG / 检查报告。
 */
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const TOOL_DIR = join(ROOT, 'src', 'tools');

// 测试跑出来的 apply 日志不要混进真实的那份（排查插件是否加载时要看它）。
process.env.SUBJKIT_APPLY_LOG = join(tmpdir(), 'dsh-subjkit-smoke-apply.log');

const failures = [];
let step = 0;

async function section(title, run) {
  step += 1;
  process.stdout.write(`\n[${step}] ${title}\n`);
  try {
    await run();
  } catch (e) {
    failures.push(title);
    process.stdout.write(`✘ ${e?.stack ?? e}\n`);
  }
}

function ok(message) {
  process.stdout.write(`✔ ${message}\n`);
}

// ---------------------------------------------------------------------------
// 1. schema 审计
// ---------------------------------------------------------------------------
await section('工具 schema 与 execute 读取的参数一致', async () => {
  const { toolDefinitions } = await import('../src/tools/index.js');
  const tools = toolDefinitions();
  assert.equal(tools.length, 3, '应有 3 个工具');

  const files = { subject_pdf: 'pdf.js', subject_figure: 'figure.js', subject_check: 'check.js' };

  for (const { spec, execute } of tools) {
    const s = spec();
    assert.equal(typeof s.name, 'string');
    assert.ok(s.description.length > 80, `${s.name} 的 description 太短`);
    assert.equal(typeof execute, 'function', `${s.name} 没有 execute`);
    assert.equal(typeof s.output?.render, 'function', `${s.name} 缺 output.render`);
    assert.equal(s.output?.schema?.type, 'object', `${s.name} 的 output.schema 必须是 object`);
    // 宿主的 output.schema 是「value schema DSL」，不是 JSON Schema：
    // 对象级 required 数组会让 defineTool 直接抛
    // "schema.required is not supported by the value schema DSL"，
    // 而 apply 会吞掉这个异常 —— 表现就是「装上了，但工具不出现」。
    assert.ok(!('required' in s.output.schema),
      `${s.name}: output.schema 不能有对象级 required 数组，必填写在属性上`);
    assert.equal(s.output.schema.properties?.text?.required, true,
      `${s.name}: output.schema 的 text 必须是 required: true`);

    const declared = Object.keys(s.parameters ?? {});
    assert.ok(declared.length > 0, `${s.name} 没有声明参数`);
    for (const [name, node] of Object.entries(s.parameters)) {
      assert.ok(typeof node.type === 'string', `${s.name}.${name} 缺 type`);
      assert.ok(!('minimum' in node || 'pattern' in node), `${s.name}.${name} 用了宿主不支持的注解`);
      assert.ok(
        typeof node.description === 'string' && node.description.length > 0,
        `${s.name}.${name} 缺 description`,
      );
    }

    const source = await readFile(join(TOOL_DIR, files[s.name]), 'utf8');
    const used = new Set([...source.matchAll(/\bargs\??\.(\w+)/g)].map((m) => m[1]));
    const missing = [...used].filter((n) => !declared.includes(n));
    const unused = declared.filter((n) => !used.has(n));
    assert.equal(missing.length, 0, `${s.name} 读了未声明的参数（会被宿主丢掉）：${missing.join(', ')}`);
    assert.equal(unused.length, 0, `${s.name} 声明了但没读的参数：${unused.join(', ')}`);
  }
  ok(`3 个工具的参数/返回值契约都对得上`);
});

// ---------------------------------------------------------------------------
// 2. 注册（mock ctx + defineTool 桩）
// ---------------------------------------------------------------------------
await section('apply() 注册工具与技能，dispose 能解绑', async () => {
  const { apply } = await import('../src/index.js');
  const silent = { error() {}, warn() {} };

  // 先验证「注册途中有一步炸了，不能把宿主启动搞崩」：
  let disposeOnFailure;
  await assert.doesNotReject(async () => {
    disposeOnFailure = await apply({
      tools: {
        register() {
          throw new Error('host refused registration');
        },
      },
      get: (key) => (key === 'skills' ? { register: () => () => {} } : undefined),
      logger: silent,
    });
  });
  assert.equal(typeof disposeOnFailure, 'function', 'apply 必须回一个 disposer，哪怕注册失败');
  disposeOnFailure();
  ok('注册抛异常时 apply 只记日志，宿主照常启动');

  // 再装一个 defineTool 桩，走完整注册路径：
  const dir = await mkdtemp(join(tmpdir(), 'subjkit-stub-'));
  try {
    const stub = join(dir, 'dsh-tools-stub.mjs');
    await writeFile(stub, 'export function defineTool(spec) { return spec; }\n', 'utf8');
    process.env.DSH_TOOLS_PATH = stub;

    const tools = [];
    const skills = [];
    const live = new Set();
    const ctx = {
      tools: {
        register(definition) {
          tools.push(definition);
          live.add(definition.name);
          return () => live.delete(definition.name);
        },
      },
      get(key) {
        if (key !== 'skills') return undefined;
        return {
          register(skill) {
            skills.push(skill);
            return () => {};
          },
        };
      },
      logger: silent,
    };

    const dispose = await apply(ctx);
    assert.deepEqual(
      tools.map((t) => t.name).sort(),
      ['subject_check', 'subject_figure', 'subject_pdf'],
    );
    assert.deepEqual(skills.map((s) => s.name).sort(), ['math-typeset', 'subject-diagram']);
    for (const skill of skills) {
      assert.ok(skill.content.length > 500, `${skill.name} 的技能正文太短`);
      assert.ok(!skill.content.includes('@@TOOL_DIR@@'), `${skill.name} 里还有未替换的 @@TOOL_DIR@@`);
      assert.ok(skill.content.includes(ROOT), `${skill.name} 的工具目录没指向本包`);
      assert.ok(skill.description.length > 10, `${skill.name} 缺 description`);
      assert.equal(skill.resourceBase?.path, ROOT);
    }
    assert.equal(live.size, 3, '3 个工具都应在注册表里');

    dispose();
    assert.equal(live.size, 0, 'dispose 之后工具必须全部解绑');
    ok(`注册 ${tools.length} 个工具 + ${skills.length} 个技能，dispose 干净`);
  } finally {
    delete process.env.DSH_TOOLS_PATH;
    await rm(dir, { recursive: true, force: true });
  }
});

// ---------------------------------------------------------------------------
// 3. 真跑三个工具
// ---------------------------------------------------------------------------
const outDir = await mkdtemp(join(tmpdir(), 'subjkit-smoke-'));

try {
  const { toolDefinitions } = await import('../src/tools/index.js');
  const byName = new Map(toolDefinitions().map((t) => [t.spec().name, t]));

  await section('subject_check 抓得到裸符号', async () => {
    const { execute } = byName.get('subject_check');
    const value = await execute({ input: join(ROOT, '示例', '公式对照.md') });
    assert.ok(value.text.includes('√'), '报告里应出现 √');
    assert.ok(/发现 \d+ 处/.test(value.text), `报告格式不对：${value.text.slice(0, 80)}`);
    ok(value.text.split('\n')[0]);
  });

  await section('subject_figure 出 SVG', async () => {
    const { execute } = byName.get('subject_figure');
    const output = join(outDir, 'incline.svg');
    const value = await execute({
      spec: { type: 'incline', angle: 30, block_label: '$m$', decompose: true },
      output,
    });
    assert.ok(existsSync(output), 'SVG 没生成');
    const svg = await readFile(output, 'utf8');
    assert.ok(svg.includes('<svg'), '不是 SVG');
    assert.ok(value.text.includes('incline'));
    ok(value.text.replace(/\n/g, ' '));
  });

  await section('subject_pdf 出带 \\sqrt \\frac 的 PDF', async () => {
    const { execute } = byName.get('subject_pdf');
    const sample = join(ROOT, '示例', '公式对照.md');
    const output = join(outDir, '公式对照.pdf');

    // 默认要先过 check：样张故意留了 9 处错误写法，必须被拦下
    await assert.rejects(() => execute({ input: sample, output }), /check 拦下|subjkit pdf 失败/);
    assert.ok(!existsSync(output), '被拦下时不应留下 PDF');

    const value = await execute({ input: sample, output, preview: true, check: false });
    assert.ok(existsSync(output), 'PDF 没生成');
    const bytes = await readFile(output);
    assert.ok(bytes.subarray(0, 4).toString() === '%PDF', '不是 PDF');
    assert.match(value.text, /\d+ 页，\d+ 条公式/);
    assert.ok(!value.text.includes('没排好'), `有公式没排好：${value.text}`);
    assert.ok(value.text.includes('_预览.png'), 'preview 没生成');
    ok(value.text.replace(/\n/g, ' '));
  });

  await section('subject_check 的 paper / report 分级', async () => {
    const { execute } = byName.get('subject_check');
    const dataDoc = join(outDir, '数据样例.md');
    await writeFile(
      dataDoc,
      ['排名 274/450，上次 405/600。', '', 'A → B，误差 ≈ 3%。'].join('\n'),
      'utf8',
    );

    const paper = await execute({ input: dataDoc });
    assert.match(paper.text, /error \d+/);
    const report = await execute({ input: dataDoc, profile: 'report' });
    assert.match(report.text, /error 0/, `report 模式不该有 error：${report.text}`);
    assert.match(report.text, /info \d+/);

    const noRatio = await execute({ input: dataDoc, profile: 'report', exclude_ratios: true });
    assert.ok(!noRatio.text.includes('274'), 'exclude_ratios 后不该再出现 274/450');
    ok(`paper 有 error；report 0 error（${report.text.split('\n')[0].trim()}）`);
  });

  await section('subject_figure 简写 / dry-run / 报错', async () => {
    const { execute } = byName.get('subject_figure');

    const shorthand = await execute({
      spec: { type: 'apparatus', parts: ['beaker', 'funnel'] },
      output: join(outDir, 'apparatus_简写.svg'),
    });
    assert.match(shorthand.text, /简写/);

    const dry = await execute({ spec: { type: 'cell', kind: 'plant' }, dry_run: true });
    assert.match(dry.text, /内置标签/);
    assert.match(dry.text, /细胞壁/);

    const plot = await execute({
      spec: { type: 'plot', functions: ['x^2-2x-3'], xmin: -2, xmax: 4 },
      output: join(outDir, 'plot_简写.svg'),
    });
    assert.match(plot.text, /补乘号/);

    await assert.rejects(
      () => execute({ spec: { type: 'cell', kind: 'plant', notes: true } }),
      /notes 是「标注数组」/,
    );
    await assert.rejects(
      () => execute({ spec: { type: 'apparatus', parts: [{ kind: 'nope' }] } }),
      /不认识/,
    );
    await assert.rejects(
      () => execute({ spec: { type: 'plot', functions: ['xy'] } }),
      /歧义/,
    );
    ok('简写能用、dry-run 给坐标、错误是中文');
  });

  await section('相对路径按会话工作目录解析', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'subjkit-cwd-'));
    try {
      await writeFile(join(dir, '相对.md'), '排名 274/450。\n', 'utf8');
      // 宿主上下文：workingDirectory.ensure(agent) 返回会话目录
      const ctx = {
        get: (key) => (key === 'workingDirectory'
          ? { ensure: async () => dir, defaultDirectory: dir }
          : undefined),
      };
      const exec = { agent: { id: 'smoke' } };

      const check = byName.get('subject_check');
      const checked = await check.execute({ input: '相对.md', profile: 'report' }, exec, ctx);
      assert.match(checked.text, /发现 1 处/, `相对 input 没找到文件：${checked.text.slice(0, 80)}`);

      const figure = byName.get('subject_figure');
      await figure.execute({ spec: { type: 'incline', angle: 30 }, output: '相对图.svg' }, exec, ctx);
      assert.ok(existsSync(join(dir, '相对图.svg')), '相对 output 没落到会话目录');
      ok(`相对 input/output 都落在会话目录（${dir}）`);
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });

  await section('参数错误有人话，不是堆栈', async () => {
    const figure = byName.get('subject_figure');
    await assert.rejects(() => figure.execute({ spec: {} }), /spec\.type/);
    const pdf = byName.get('subject_pdf');
    await assert.rejects(() => pdf.execute({}), /input 是必填项/);
    await assert.rejects(
      () => pdf.execute({ input: join(outDir, '不存在.md') }),
      /subjkit pdf 失败/,
    );
    ok('缺参数 / 文件不存在都给出可读的报错');
  });
} finally {
  await rm(outDir, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// 7. 清单文件（插件管理器要读的东西）
// ---------------------------------------------------------------------------
await section('package.json / cordis.patch.yml / dsh.plugin.json / locale / icon', async () => {
  const pkg = JSON.parse(await readFile(join(ROOT, 'package.json'), 'utf8'));
  assert.equal(pkg.name, 'dsh-subjkit');
  assert.equal(pkg.type, 'module');
  assert.equal(pkg.main, './src/index.js');
  assert.equal(pkg.exports?.['.'], './src/index.js');
  assert.equal(pkg.dsh?.bundle?.patch, './cordis.patch.yml');
  assert.equal(pkg.peerDependenciesMeta?.['@deepseek-ai/dsh-tools']?.optional, true,
    'dsh-tools 必须是 optional peer，否则宿主里没有它时装不上');
  assert.ok(existsSync(join(ROOT, 'src', 'index.js')), 'main 指向的文件不存在');

  // `files` 里写了不存在的路径，npm 打包后就是缺文件——这里逐个查。
  for (const entry of pkg.files ?? []) {
    assert.ok(existsSync(join(ROOT, entry)), `files 里的 "${entry}" 不存在`);
  }

  const patch = await readFile(join(ROOT, 'cordis.patch.yml'), 'utf8');
  assert.match(patch, /^- insert:/m, 'patch 必须是 insert 列表');
  assert.match(patch, /id:\s*dsh-subjkit/);
  assert.match(patch, /name:\s*dsh-subjkit/);

  const plugin = JSON.parse(await readFile(join(ROOT, 'dsh.plugin.json'), 'utf8'));
  assert.equal(plugin.name, pkg.name);
  assert.equal(plugin.version, pkg.version, 'dsh.plugin.json 与 package.json 版本不一致');
  assert.equal(plugin.entry?.name, pkg.name);
  assert.ok(plugin.entry?.inject?.includes('tools'));

  const entry = await import('../src/index.js');
  assert.equal(entry.name, pkg.name);
  assert.deepEqual(entry.inject, ['tools']);
  assert.equal(typeof entry.apply, 'function');

  for (const locale of ['zh.json', 'en.json']) {
    const json = JSON.parse(await readFile(join(ROOT, 'locale', locale), 'utf8'));
    assert.ok(json.meta?.title, `${locale} 缺 meta.title`);
    assert.ok(json.meta?.description, `${locale} 缺 meta.description`);
  }

  const icon = await readFile(join(ROOT, 'icon.svg'), 'utf8');
  assert.ok(icon.trimStart().startsWith('<svg'), 'icon.svg 不是 SVG');
  assert.ok(icon.length < 256 * 1024, 'icon.svg 超过 256 KiB');

  ok('清单字段、patch、locale、icon 都齐');
});

await rm(process.env.SUBJKIT_APPLY_LOG, { force: true });

process.stdout.write(
  failures.length === 0
    ? '\n✔ 插件验证全部通过\n'
    : `\n✘ ${failures.length} 项失败：${failures.join(' / ')}\n`,
);
process.exit(failures.length === 0 ? 0 : 1);
