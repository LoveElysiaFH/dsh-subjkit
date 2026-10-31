/**
 * run.js — 起子进程跑 subjkit CLI，从结果文件取返回值。
 *
 * **为什么不用 stdout**：DSH 的沙箱里 `spawn` 用默认的 `stdio: 'pipe'` 可能直接
 * EPERM（管道不可用），模型会看到一条莫名其妙的失败。所以这里
 * `stdio: 'ignore'`，CLI 用 `--result-json` 把结果写进临时目录，Node 再读回来。
 * 成功和失败都走同一个文件，所以没有「退出码非零但什么都不知道」的情况。
 */
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { cliPath, pythonExe } from './paths.js';

const DEFAULT_TIMEOUT_MS = 240_000;

/**
 * 跑一次 CLI 子命令，返回结果信封里的 `data`。
 *
 * @param {string} command `pdf` / `fig` / `check`
 * @param {object} [options]
 * @param {string[] | ((dir: string) => string[])} [options.args]
 *   子命令参数。需要在临时目录里先写输入（如图示 spec）时传函数。
 * @param {(dir: string) => Promise<void>} [options.prepare]
 *   起进程前把临时输入写进 `dir`。
 * @param {string} [options.cwd] 子进程工作目录（默认继承会话目录）
 * @param {number} [options.timeoutMs]
 * @returns {Promise<any>}
 */
export async function callCli(command, {
  args = [],
  prepare,
  cwd,
  timeoutMs = DEFAULT_TIMEOUT_MS,
} = {}) {
  const dir = await mkdtemp(join(tmpdir(), 'dsh-subjkit-'));
  try {
    if (prepare) await prepare(dir);
    const resultPath = join(dir, 'result.json');
    const rest = typeof args === 'function' ? args(dir) : args;
    const exitCode = await run(
      pythonExe(),
      [cliPath, command, ...rest, '--result-json', resultPath],
      { cwd, timeoutMs },
    );
    const payload = await readPayload(resultPath, command, exitCode);
    if (payload?.ok !== true) {
      throw new Error(`subjkit ${command} 失败：${payload?.error ?? 'CLI 没有给出原因'}`);
    }
    return payload.data;
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

/** 读结果信封；文件不在说明 Python 根本没跑起来或中途死了。 */
async function readPayload(resultPath, command, exitCode) {
  let text;
  try {
    text = await readFile(resultPath, 'utf8');
  } catch {
    throw new Error(
      `subjkit ${command} 没有写出结果（退出码 ${exitCode}）。`
      + '先在这个插件目录执行 `python subjkit.py doctor`，按提示补 Node.js / MathJax / Edge。',
    );
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`subjkit ${command} 的结果文件不是合法 JSON（退出码 ${exitCode}）。`);
  }
}

/** 等子进程结束，超时就杀掉。stdio 忽略，所以这里只能看退出码。 */
function run(exe, argv, { cwd, timeoutMs }) {
  return new Promise((resolve, reject) => {
    let child;
    try {
      child = spawn(exe, argv, { cwd, stdio: 'ignore', windowsHide: true });
    } catch (e) {
      reject(startFailure(exe, e));
      return;
    }

    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      try {
        child.kill();
      } catch {
        // 已经退出了
      }
      reject(new Error(`subjkit 执行超时（${Math.round(timeoutMs / 1000)} 秒）。`));
    }, timeoutMs);

    child.on('error', (e) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(startFailure(exe, e));
    });
    child.on('close', (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(code ?? -1);
    });
  });
}

function startFailure(exe, error) {
  if (error?.code === 'ENOENT') {
    return new Error(
      `找不到 Python 解释器 "${exe}"。装 Python 3.10+，`
      + '或把环境变量 SUBJKIT_PYTHON 指向 python.exe 的完整路径。',
    );
  }
  return new Error(`启动 ${exe} 失败：${error?.message ?? error}`);
}
