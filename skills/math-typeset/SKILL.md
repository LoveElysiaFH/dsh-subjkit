---
name: math-typeset
description: 排版含公式的数学/物理/化学讲义、试卷、答案并输出 PDF；修复根号上横线盖不住、分数写成斜杠、集合/希腊字母显示成替代字形的问题。
---

# 公式排版（subjkit）

> 装了 `dsh-subjkit` 插件时，直接用工具 `subject_check` / `subject_pdf`，不用命令行。
> 没装插件（或要写脚本）时用下面的命令行；`@@TOOL_DIR@@` 指向本仓库。

## 何时使用

要出**数学、物理、化学**的试卷、讲义、答案、学情报告，或现有 PDF 里的公式出现下列任一情况：

- 根号只有「√」一个符号，上横线盖不住后面的字符；
- 分数写成 `1/2`、`1/a`、`(-b±√…)/(2a)`；
- `∈ ∩ ≤ ≠ ∅ π α ⊥ ∠` 等符号大小、基线不对，像换了一种字体；
- PDF 里的公式是点阵图，放大发虚。

这些问题的根因是：正文直接写了 Unicode 数学字符，浏览器只能回退到 Cambria Math / Segoe UI Symbol。本工具把公式交给 MathJax 排成**矢量 SVG**，再交给 Edge 打印，PDF 里的公式与正文风格一致，且不依赖阅读者的字体。

## 三条硬规则（违反任意一条，学生就会看到替代符号）

1. **所有数学式子必须包进 `$...$`（行内）或 `$$...$$`（独立成行）**。正文里禁止裸写 `√ ∈ ≤ ≥ ≠ ≈ ± × ÷ π α β θ ° ² ³ ₁ ₂ ∩ ∪ ⊂ ∅ ∞ ∑ ∫ ∠ △ ⊥ ∥ → ⇒` 等符号。
2. **根号用 `\sqrt{...}`，花括号里写完整被开方式**：`$\sqrt{b^2-4ac}$`、`$\sqrt{x+1}$`、`$\sqrt[3]{x+2}$`。不要写 `√(b²-4ac)`。
3. **分数用 `\frac{分子}{分母}`**：`$\frac{1}{2}$`、`$\frac{-b\pm\sqrt{b^2-4ac}}{2a}$`。**禁止** `1/2`、`1/a`。行内需要看清时用 `\dfrac`。

## 用插件工具（推荐）

装了 `dsh-subjkit` 插件后，这两个工具随插件一起可用：

| 工具 | 做什么 | 关键参数 |
|---|---|---|
| `subject_check` | 检查裸符号 / 斜杠分数 / `x^2`，结果分 error / warn / info 三级 | `input`、`profile`、`exclude_ratios` |
| `subject_pdf` | Markdown → PDF，公式自动转矢量；**出图前自己先跑一遍 check** | `input`（必填）、`output`、`split`、`preview`、`preview_pages`、`title`、`subtitle`、`footer`、`check`、`check_only` |

顺序和命令行一样：`subject_check` 改到 **0 处** → `subject_pdf` 出 PDF。
现在这条规矩是**工具自己兜住的**：`subject_pdf` 发现 error 会直接拒绝出图并列出问题；
真要带着 error 出图，显式传 `check: false`。

### 先想清楚：这是公式，还是数据？

同一句 `274/450`，在试卷里是分数，在学情报告里是排名分母。搞错了要么漏改、要么把表格撑爆。

| 文档 | `profile` | 行为 |
|---|---|---|
| 试卷、讲义、答案（有公式） | `paper`（默认） | 一切像公式却没包 `$...$` 的写法都是 **error** |
| 学情报告、院校参考表（表格为主） | `report` | 数字比值（`274/450`）与行文箭头（`→`、`≈`）**降级为 info**，不再算 error |

`report` 模式下 error 归零，`subject_pdf` 就能正常出图；info 只是提示，**不要**照着改成 `\frac`。
实在懒得看 info，加 `exclude_ratios` / `--exclude-ratios` 直接跳过纯数字比值。

### 表格跨页怎么处理

- **长表格允许跨页**，且**表头在每页重复**（`thead` 自动重复），一行不会被劈成两半；
- 要让某一块整块不跨页（小结表、图的题），在它前面单独写一行 `<!--keep-->`，下一块自动套 `.keep`；
- 也可以直接写 `<div class="keep">…</div>` 包住任意 HTML 块。

> 数据报告（六列、几十行、几乎没公式）仍然走 HTML 管线：可控列宽、表格更好看。
> `subject_pdf` 的优势在公式，不在复杂表格。

## 命令（没装插件时）

工具目录：`@@TOOL_DIR@@`。下面的命令在 PowerShell 里执行，路径含中文时用引号包住。

```powershell
# 1) 先检查源文件里有没有裸符号 / 斜杠分数 / x^2 写法
python "@@TOOL_DIR@@\subjkit.py" check "试卷.md"

# 2) 生成 PDF（公式自动转矢量）
python "@@TOOL_DIR@@\subjkit.py" pdf "试卷.md" -o "试卷.pdf"

# 3) 打印件：同时拆奇数页/偶数页
python "@@TOOL_DIR@@\subjkit.py" pdf "试卷.md" -o "试卷.pdf" --split

# 4) 生成后立刻导出 PNG 预览，自己先看一遍
python "@@TOOL_DIR@@\subjkit.py" pdf "试卷.md" -o "试卷.pdf" --preview

# 5) 单条公式 → SVG（可放进 HTML/PPT/LaTeX）
python "@@TOOL_DIR@@\subjkit.py" math "\frac{-b\pm\sqrt{b^2-4ac}}{2a}" -o 求根公式.svg --display
```

`check` 应做到 **0 处**再生成 PDF。它会把每个问题标到「行:列 + 建议写法」。旧版 HTML 试卷也能直接查（会跳过标签，只查正文）：

```powershell
python "@@TOOL_DIR@@\subjkit.py" check "旧试卷.html"
```

## Markdown 写法

支持：标题、段落、列表、表格、引用、代码块、图片、`**加粗**`、`*下划线强调*`、`\newpage` 分页，以及 `$...$` / `$$...$$`。

文件开头可写 front matter 控制版式：

```markdown
---
title: 数学 · 函数专项卷 02
subtitle: 满分 60 分　｜　限时 40 分钟
banner: 非选择题（打印）
footer: 第 1 页 / 共 2 页
margin: 14mm 14mm 12mm 14mm
---
```

试卷常用块（直接写 HTML）：

```html
<div class="banner">非选择题（打印）</div>
<div class="q"><span class="qno">1.</span> <span class="pts">（5 分）</span>题干……</div>
<div class="work" style="height:30mm"><div class="hint">过程：</div></div>
<div class="note">提示：……</div>
<div class="foot">本份为打印件</div>
```

## 图片与图示

先用 `subject-diagram` 技能生成 `.svg`，再在 Markdown 里按相对路径引用：

```markdown
![受力分析](图/受力_水平面.svg)
```

`pdf` 会把图片转成 data URI 嵌入 HTML，所以临时目录渲染不会丢图。

## 推荐流程

1. 写 `试卷.md`；所有式子用 `$...$`，根号带花括号，分数用 `\frac`。
2. `check` → 改到 0 处。
3. `pdf --preview` → 用图片查看工具看首页（重点看根号上横线、分数横线、集合符号）。
4. 确认无误再 `--split` 出打印件；答案单独一个 PDF。
5. 学生做完再给答案，答案文件名带「答案」。

## 排错

| 现象 | 处理 |
|---|---|
| PDF 里出现红色「公式错误」 | TeX 写错；看终端里 `⚠ 有 N 条公式没排好` 给出的原文，补 `}`、改 `\` |
| 根号仍然很短 | 被开方式没全放进花括号：`\sqrt{b^2-4ac}` ✅，`\sqrt{b^2}-4ac` ❌ |
| 分数仍是斜杠 | 还在正文里写 `1/2`；用 `$\frac{1}{2}$` |
| `check` 报 `x^2` | 改为 `$x^{2}$` |
| 找不到 Edge / node | 运行 `python "@@TOOL_DIR@@\subjkit.py" doctor`，按提示装 Edge 或 Node.js |
| 中文变方框 | 检查 `assets/base.css` 的字体栈，Windows 需有 SimSun/SimHei |

## 注意

- 这是**打印排版**工具，不做 Word 编辑；需要 .docx 用 `office-docx` 技能。
- 公式是 MathJax 的 SVG，PDF 里是矢量路径，放大不会虚。
- 不要为了「快」退回 Unicode 符号或 `a/b`；这正是要修的问题。
