/**
 * skills.js — 把 `skills/` 下的 SKILL.md 注册成 DSH 技能。
 *
 * 装上这个插件，两个技能就一起出现，不需要再跑 `python install.py`：
 * 工具负责「做事」，技能负责「什么时候用、公式怎么写」。
 * `install.py` 仍然保留，给只想要技能、不装插件的会话用。
 *
 * 技能服务是可选依赖（`ctx.get('skills')`）：拿不到就只注册工具，不影响启动。
 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

import { packageRoot } from './paths.js';

const SKILL_DIRS = ['math-typeset', 'subject-diagram'];
const PROVIDER = 'dsh-subjkit';

/**
 * 注册本包自带的技能。
 *
 * @param {object} ctx 插件上下文
 * @returns {Array<() => void>} 注销函数
 */
export function registerSkills(ctx) {
  const skills = ctx?.get?.('skills');
  if (!skills?.register) return [];

  const disposers = [];
  for (const dir of SKILL_DIRS) {
    try {
      const skill = readSkill(join(packageRoot, 'skills', dir, 'SKILL.md'), dir);
      if (skill) disposers.push(skills.register(skill));
    } catch (e) {
      // 技能坏了不能连累工具
      try {
        ctx?.logger?.warn?.(`[dsh-subjkit] 技能 ${dir} 注册失败：${e?.message ?? e}`);
      } catch {
        // 日志也失败就算了
      }
    }
  }
  return disposers;
}

/** 读一个 SKILL.md：front matter 给 name/description，正文就是技能内容。 */
function readSkill(file, fallbackName) {
  if (!existsSync(file)) return null;
  const text = readFileSync(file, 'utf8').replace(/\r\n/g, '\n');

  const front = /^---\n([\s\S]*?)\n---\n?/.exec(text);
  const head = front ? front[1] : '';
  let body = front ? text.slice(front[0].length) : text;

  let name = fallbackName;
  let description = '';
  for (const line of head.split('\n')) {
    const m = /^([A-Za-z_][\w-]*):\s*(.*)$/.exec(line.trim());
    if (!m) continue;
    if (m[1] === 'name') name = m[2].trim();
    else if (m[1] === 'description') description = m[2].trim();
  }
  if (!description) {
    description = body.split('\n').map((l) => l.trim()).find((l) => l && !l.startsWith('#')) ?? name;
  }

  // 正文里的 @@TOOL_DIR@@ 指向仓库根目录（install.py 装技能时做同样的替换）。
  body = body.split('@@TOOL_DIR@@').join(packageRoot);

  return {
    name,
    description,
    source: 'custom',
    provider: PROVIDER,
    // 技能里提到的 `subjkit.py`、`assets/base.css` 都是相对仓库根目录的。
    resourceBase: { kind: 'directory', path: packageRoot },
    invocation: { modelInvocable: true, userInvocable: true },
    content: body,
  };
}
