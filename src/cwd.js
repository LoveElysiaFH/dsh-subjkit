/**
 * cwd.js — 把「相对路径」解析到**会话的工作目录**。
 *
 * 子进程继承的是 DSH 宿主的 cwd（在桌面版里是 profile 目录），不是用户在会话里
 * 选的目录。所以 `subject_pdf(input: "试卷.md")` 不显式传 cwd 就会去 profile 目录下找，
 * 白白报「文件不存在」。这里用 workingDirectory 服务把会话目录拿出来。
 *
 * 服务本身是可选的（不在所有组合里都挂）：拿不到就返回 undefined，
 * 子进程继续继承宿主 cwd —— 行为退化，但不炸。
 */

/**
 * @param {object} ctx  插件上下文
 * @param {object} [exec] 宿主的 ToolRunContext（里面有 agent）
 * @returns {Promise<string|undefined>}
 */
export async function sessionCwd(ctx, exec) {
  try {
    const wd = ctx?.get?.('workingDirectory');
    if (!wd) return undefined;
    if (wd.ensure && exec?.agent) return await wd.ensure(exec.agent);
    return wd.defaultDirectory ?? undefined;
  } catch {
    return undefined;
  }
}
