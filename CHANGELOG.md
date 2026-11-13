# 变更日志

本文件只记「会影响使用者写法」的变化。规则意图见 `skills/` 与使用方自己的
学科工具规范（出卷走 `subject_pdf`、数据报告走 HTML 的那份）。

---

## 0.3.1 — 2026-11-13

**起因**：中央控制会话复测 `subject_pdf` 已自行恢复（故障期定位结论见下），但另有
4 条排版/判定问题需要修，另加一条「报告摘要要更醒目」。

### 修了什么

| 编号 | 问题 | 处理 |
|---|---|---|
| 必修 1 | 引用块里的 `##` 原样印出，且两行粘成一段 | 引用块内容改为**递归按 Markdown 解析**：标题、列表、表格、硬换行在引用块里全部成立 |
| 必修 2 | 行尾两个空格不产生硬换行 | 实现 CommonMark 硬换行。两个 bug 一起修：①行尾空格在判定前被 `rstrip` 吃掉；②`<br>` 用错了行（插在当前行之前，导致整列错开一行，最后一行常丢） |
| 必修 3 | 行文里的 `≥ ≤ ≠` 判 error，拦住整份 PDF | 按**左侧上下文**判定：左边（跳过空白）是汉字/中文标点 → 视为行文，降为 `warn`；左边是变量、数字或行首 → 仍 `error` |
| 隐患 4 | `read_css()` 用 `utf-8` 读，遇 BOM 会让整段样式失效 | 改 `utf-8-sig`，自动剥 BOM；`read_css(path)` 支持传入路径，便于测试 |
| 报告摘要 | warn 与 error 混在一张表里，容易误以为「被 warn 拦住了」 | 报告**第一行**先给`error N 处（会拦截出 PDF / 不拦截）｜warn M 处（不拦截，可改可不改）｜info K 处（提示）` |
| 故障可诊断 | `Edge 未生成 PDF（exit=0）` 没有任何线索 | 报错里带上：输出路径、输出目录是否存在/可写、全量 stderr（原来只截 600 字，常常是空的）；`--user-data-dir` 的临时目录在起进程前做一次写权限自检 |

> 故障期结论留档：**Edge 在输出路径写不进去时也会 `exit=0` 且不写文件**，只在 stderr 留一行
> `Failed to write`。所以 `exit=0` 不能作为「Edge 正常」的证据。

### 行为变化

- `check` 的报告多了一行摘要（第一行），表格列不变。
- `paper` 档下，**行文里的** `≥ ≤ ≠ ≈ ≡ ∼ ∽` 从 `error` 降为 `warn`，不再拦 PDF；
  数学语境（`当 x ≥ 1 时`、`≥20`、`A∩B`）**仍然是 `error`**。
- 行尾两个空格现在真的会产生换行（以前不生效）；靠「空行合并」凑出来的版式会变。

### 兼容性

- 没有改任何工具名、字段名、模板名；六科提示词不用动。
- `report` 档行为不变；`--strict` 仍是「error/warn 才失败」。

---

## 0.3.0 — 2026-10-31

**起因**：中央控制会话在六科提示词里把出卷切到 `subject_pdf` 后，实测反馈了 8 条问题（P0×2、P1×3、P2×3）。
本版全部处理，不改任何现有字段名，旧写法继续能跑。

### 修了什么

| 编号 | 问题 | 处理 |
|---|---|---|
| P0-1 | `subject_check` 对数据文档误报 127 处（`274/450`、行文箭头） | 新增 `profile: paper \| report` 与三级 severity；`report` 下数字比值与行文箭头降级为 `info`，`error` 归零 |
| P0-2 | 图示参数报错是 Python traceback（`string indices must be integers`、`'bool' object is not iterable`、`invalid decimal literal`） | 新增校验层 `subjkit/diagrams/validate.py`：所有坏 spec 都返回中文说明 + 最小可运行示例；不再出现 traceback |
| P1-1 | `plot` 图例压在曲线上、无法指定位置；点标签被曲线穿过 | 新增 `legend: auto\|ur\|ul\|br\|bl\|none`（默认 `auto` 自动避让）、`points[].label_offset` |
| P1-2 | `plot` 没有刻度、y 范围必须手给 | `new_figure` 对 plot 重新打开坐标轴；新增 `ticks` / `grid` / `xstep` / `ystep`；`y` 省略时按函数值域自动算（10% 余量） |
| P1-3 | `cell` 自定义标注压住内置标签 | 内置标签改为数据表 `CELL_LABELS`；新增 `show_builtin_labels`；自定义标注自动纵向错开；`--dry-run` 可打印内置标签坐标 |
| P2-1 | 缺「只校验不渲染」入口 | `subject_figure: dry_run` / `fig --dry-run`；`subject_pdf: check_only` / `pdf --check-only` |
| P2-2 | `subject_pdf` 不联动 `subject_check` | `subject_pdf` 默认先跑 check（paper），有 `error` 就拒绝出图；`check: false` / `--no-check` 可跳过 |
| P2-3 | 表格跨页行为未明确 | `thead` 每页重复、行不劈开；新增 `<!--keep-->` 标记与 `.keep` 类（整块不跨页） |
| — | 相对路径落到了 profile 目录（实测第 4 步暴露） | 三个工具改用 `workingDirectory.ensure(agent)` 取会话目录，子进程 `cwd` 指过去；`input`/`output` 写相对路径现在按会话目录解析（工具描述早就这么写，之前是假的） |

### 新参数（全部可选，有默认值）

| 工具 / 命令 | 新参数 | 默认 | 说明 |
|---|---|---|---|
| `subject_check` / `check` | `profile` / `--profile` | `paper` | `paper` 严格；`report` 把数据比值、行文箭头降为 `info` |
| `subject_check` / `check` | `exclude_ratios` / `--exclude-ratios` | `false` | 直接跳过 `274/450` 这类纯数字比值 |
| `check` | `--json` | — | 把结果打成 JSON（stdout） |
| `subject_pdf` / `pdf` | `check` / `--no-check` | 检查开启 | 关掉出图前的自动 check |
| `subject_pdf` / `pdf` | `check_only` / `--check-only` | `false` | 只检查、不出 PDF |
| `subject_figure` / `fig` | `dry_run` / `--dry-run` | `false` | 只校验 spec，不出图 |
| `plot` | `legend` | `auto` | `auto/ur/ul/br/bl/none`，`legend_loc` 仍兼容 |
| `plot` | `ticks` / `grid` / `xstep` / `ystep` | `true` / `true` / 自动 / 自动 | 刻度与网格 |
| `plot` | `points[].label_offset` | `[0.18, 0.22]` | `offset` 是同一个意思 |
| `plot` | `xmin/xmax/ymin/ymax` | — | 旧别名，等价于 `x:[min,max]` / `y:[min,max]` |
| `apparatus` | `parts` 可整组写字符串 | — | `["beaker","funnel"]` 自动从左到右排 |
| `cell` | `show_builtin_labels` | `true` | `false` 只保留自定义标注 |

### 写法对照（都能跑，左边是新推荐）

| 场景 | 现在 | 以前 |
|---|---|---|
| 检查试卷 | `subject_check(input, profile: "paper")` | `subject_check(input)` |
| 检查学情报告 | `subject_check(input, profile: "report")` | 会报 127 处误报 |
| 函数表达式 | `"x^2-2x-3"`（自动补乘号，结果里会说明） | `"x^2-2*x-3"` |
| x 范围 | `"x": [-2, 4]` | `"xmin": -2, "xmax": 4`（仍兼容） |
| 图例 | `"legend": "auto"` | `"legend_loc": "upper left"`（仍兼容） |
| 仪器简写 | `"parts": ["beaker", "funnel"]` | 必须 `[{"kind": "beaker", "at": [0,0]}]` |
| 细胞标注 | `"notes": [{"text","at","target"}]` | 一样；但传 `true` 现在会给出明确报错 |

### 行为变化（需要注意）

1. **`subject_pdf` 默认会拦错误**：源文件有 `error` 就不出 PDF，退出码 `3`。
   六科现有流程里凡是「本来就带裸符号」的稿子，需要先改到 0，或显式 `check: false`。
2. **`check --strict` 的含义收窄**：只有 `error`/`warn` 才失败，`info` 不算。
   这样 `report` 模式下的纯数据文档不会让 CI 变红。
3. **`plot` 现在有刻度**（以前整个坐标轴是关掉的）。图会比以前略窄一点，因为要给刻度数字留边距。

### 内部

- 表达式解析独立成 `subjkit/diagrams/expr.py`（分词补乘号 + 中文报错），`mathfig.compile_expr/make_fn` 仍是原路径，老代码不断。
- `figures.render()` 改为「先 `normalize()` 再画」，模板函数不再猜参数；新增 `prepare()` / `render_normalized()` 供 dry-run 复用。
- 测试：`tests/test_regressions.py`（11 条，一条对应一个反馈），并入 `tests/test_all.py` 第 5 段；
  `tests/plugin_smoke.mjs` 增至 9 段。

---

## 0.2.0 — 2026-10-31

- 从「技能包 + Python CLI」升级为**真正的 DSH 插件**：`dsh.plugin.json` + `src/index.js` + 3 个工具
  （`subject_pdf` / `subject_figure` / `subject_check`），插件启动时一并注册 `math-typeset`、
  `subject-diagram` 两个技能。
- CLI 新增 `--result-json`：插件用 `spawn(stdio: 'ignore')` + 结果文件通信，不依赖子进程 stdout。
- 修 `defineTool` 的 value schema DSL 问题（对象级 `required` 数组会被拒绝，表现是「装上了但工具不出现」）。

## 0.1.0

- Markdown → PDF（MathJax SVG + Edge 无头打印）、13 个学科图示模板、裸符号检查器。
