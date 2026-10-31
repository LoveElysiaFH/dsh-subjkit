/**
 * paths.js — 这个包自己的位置，以及 Python 解释器和 CLI 入口。
 *
 * 插件里所有路径都从 `import.meta.url` 推出来，不依赖 process.cwd()：
 * 会话的工作目录是用户的项目目录，不是插件目录。
 */
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url)); // <pkg>/src

/** 包根目录（package.json 所在处）。 */
export const packageRoot = dirname(here);

/** `subjkit.py` 的绝对路径。插件永远走和命令行同一个入口。 */
export const cliPath = join(packageRoot, 'subjkit.py');

/**
 * Python 解释器：默认用 PATH 里的 `python`。
 * 有些机器只装了 py launcher 或 Microsoft Store 版，用 SUBJKIT_PYTHON 指过去。
 */
export function pythonExe() {
  return process.env.SUBJKIT_PYTHON || 'python';
}
