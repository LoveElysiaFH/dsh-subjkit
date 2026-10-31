/**
 * index.js — dsh-subjkit 的 DSH 插件入口。**只做注册**：
 *
 *   subject_pdf      Markdown → 打印用 PDF（公式是矢量 SVG）
 *   subject_figure   物理/数学/化学/生物/语文图示 → SVG / PNG
 *   subject_check    找出正文里用字符代替 TeX 的地方
 *
 * 外加两个技能（`math-typeset` / `subject-diagram`）—— 工具负责「做事」，
 * 技能负责「什么时候用、公式怎么写」。所以装上插件就等于装上了两者的文档。
 *
 * 契约要点（对着 @deepseek-ai/dsh-tools 的运行时行为核对的）：
 *  - `apply` 返回 disposer（把所有注册的返回值串起来），插件卸载时才会解绑；
 *  - `execute` 返回的值要过 `output.schema`；
 *  - 宿主按 `parameters` 过滤入参，**schema 没声明的参数会被静默丢掉**，
 *    所以每个工具读了哪些 args 必须和它自己的 spec 对上（见 tools/）。
 */
import { appendFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { registerSkills } from './skills.js';
import { toolDefinitions } from './tools/index.js';

export const name = 'dsh-subjkit';
export const inject = ['tools'];

/**
 * 插件「到底加载了没」的落盘痕迹。
 *
 * 桌面版看不到宿主日志，而 apply 的异常又被下面的 catch 吞掉（不能让应用起不来），
 * 于是最糟的情况是「装上了、没报错、工具就是不出来」——这条日志就是为终结这种排查。
 * 文件在系统临时目录：`dsh-subjkit-apply.log`（`SUBJKIT_APPLY_LOG` 可改路径，测试用）。
 */
const APPLY_LOG = process.env.SUBJKIT_APPLY_LOG || join(tmpdir(), 'dsh-subjkit-apply.log');

function note(line) {
  try {
    appendFileSync(APPLY_LOG, `[${new Date().toISOString()}] ${line}\n`, 'utf8');
  } catch {
    // 连日志都写不了就算了
  }
}

export async function apply(ctx) {
  // disposers 必须先声明：写在后面会撞上 const 的暂时性死区，
  // 于是「注册成功了但解绑函数没登记」，而且错误还会被下面的 catch 吞掉。
  const disposers = [];
  try {
    // 技能先注册：它不依赖 dsh-tools，工具加载失败时技能也还在。
    for (const dispose of registerSkills(ctx)) disposers.push(dispose);

    const defineTool = await loadDefineTool();
    for (const tool of toolDefinitions()) {
      // 第三个参数把插件 ctx 传进 handler：handler 要用 workingDirectory 解析会话目录。
      disposers.push(ctx.tools.register(defineTool({
        ...tool.spec(),
        execute: (args, exec) => tool.execute(args, exec, ctx),
      })));
    }
    note(`loaded: ${disposers.length} registrations`);
    return () => disposeAll(disposers);
  } catch (e) {
    // **最坏的情况是插件不能用，不是应用起不来**。apply 里的异常一律吞掉并记录。
    try {
      ctx?.logger?.error?.(`[dsh-subjkit] 加载失败：${e?.stack ?? e}`);
    } catch {
      // 连日志都写不了就算了
    }
    note(`FAILED: ${e?.stack ?? e}`);
    // SUBJKIT_DEBUG=1 时把错误抛出去——否则「插件静默不工作」很难查。
    if (process.env.SUBJKIT_DEBUG) throw e;
    return () => disposeAll(disposers);
  }
}

function disposeAll(disposers) {
  for (const dispose of disposers.reverse()) dispose?.();
}

/**
 * 解析宿主的 dsh-tools。正常安装时裸包名就能解析；
 * 本地开发/测试时用 DSH_TOOLS_PATH 指向安装里的 lib/index.js。
 */
async function loadDefineTool() {
  try {
    const mod = await import('@deepseek-ai/dsh-tools');
    if (mod?.defineTool) return mod.defineTool;
  } catch {
    // 落到环境变量
  }
  const override = process.env.DSH_TOOLS_PATH;
  if (override) {
    const { pathToFileURL } = await import('node:url');
    const mod = await import(pathToFileURL(override).href);
    if (mod?.defineTool) return mod.defineTool;
  }
  throw new Error('找不到 @deepseek-ai/dsh-tools（本地调试时用 DSH_TOOLS_PATH 指向 lib/index.js）');
}
