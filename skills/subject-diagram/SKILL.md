---
name: subject-diagram
description: 生成物理电路/受力/斜面/光路、数学函数图/几何/数轴/韦恩图、化学装置与分子结构、生物细胞/流程图、语文田字格等矢量图示。
---

# 学科图示（subjkit）

> 装了 `dsh-subjkit` 插件时，直接用工具 `subject_figure`，不用命令行。
> 没装插件（或要写脚本）时用下面的命令行；`@@TOOL_DIR@@` 指向本仓库。

## 何时使用

需要给试卷、讲义、答案配图，而不是用文字描述图形时：

- 物理：电路图、受力分析、斜面、凸透镜成像光路；
- 数学：函数图像、平面几何、数轴、韦恩图；
- 化学：常用仪器装置、分子结构式（SMILES）；
- 生物：植物/动物细胞、过程流程；
- 语文：田字格/米字格练字纸（带拼音）。

输出是**真矢量**（SVG）或 300 dpi PNG，可直接放进 PDF，不会出现截图模糊。

## 用插件工具（推荐）

`subject_figure` 的参数只有三个：

| 参数 | 说明 |
|---|---|
| `spec` | 必填，包含 `type` 的 JSON 对象，例如 `{"type":"incline","angle":30,"decompose":true}` |
| `output` | 输出文件；扩展名决定格式（`.svg` 进 PDF，`.png` 用来看效果）。默认 `figure.svg` |
| `dpi` | 仅 PNG，72~600，默认 300 |

画完用图片查看工具看一眼再交付（重点：箭头是否被裁、标签是否重叠）。要嵌进试卷就把 `output` 写成 `.svg`，再在 Markdown 里按相对路径引用。

## 命令（没装插件时）

工具目录：`@@TOOL_DIR@@`。

```powershell
# 从 JSON 文件生成（复杂图推荐）
python "@@TOOL_DIR@@\subjkit.py" fig --spec "图.json" -o "图.svg"

# 直接给 JSON 字符串
python "@@TOOL_DIR@@\subjkit.py" fig circuit --json '{"nodes":{"A":[0,0],"B":[5,0]},"elements":[{"kind":"battery","from":"A","to":"B"}]}' -o "电路.svg"

# 生成 PNG 预览（自己先看，再嵌进文档）
python "@@TOOL_DIR@@\subjkit.py" fig --spec "图.json" -o "图.png"

# 看有哪些模板
python "@@TOOL_DIR@@\subjkit.py" doctor
```

JSON 里的 `type` 决定模板；如果命令里已经给了模板名前缀（如 `fig circuit`），可以省略 `type`。

## 通用规则

- 坐标系 **y 轴向上**，单位任意（建议图宽 4~6）。
- 文字标签可以直接写中文；**数学符号放在 `$...$` 里**，例如 `"$R_1=2\\,\\Omega$"`、`"$mg\\sin\\theta$"`。不要在一个字符串里混中文和 `$...$` 公式，拆成两个标签。
- 图里不要用 ASCII 字符拼图形，也不要用 Unicode 制表符。
- 进 PDF 用 `.svg`；发到聊天/屏幕预览用 `.png`。
- 生成后一定用图片查看工具看一眼，重点检查：箭头是否被裁掉、标签是否重叠、符号是否正常。

### 先校验，再出图

`--dry-run`（工具参数 `dry_run: true`）只校验 spec、不写文件，并把「我替你改了什么」列出来。
参数写错时返回的是**中文说明 + 最小可运行示例**，不是 Python traceback：

```powershell
python "@@TOOL_DIR@@\subjkit.py" fig --spec 图.json --dry-run
```

`cell` 的 dry-run 还会打印**内置标签坐标**，照着挑空位加自定义标注，不用先出图猜。

## 模板速查

### 物理

**电路 `circuit`**：先布节点坐标，再把元件接在两点之间。

```json
{
  "type": "circuit", "size": [5.8, 3.2],
  "nodes": {"A": [0,0], "B": [5,0], "C": [5,2.6], "D": [0,2.6]},
  "elements": [
    {"kind": "battery", "from": "A", "to": "B", "label": "$6\\,\\mathrm{V}$"},
    {"kind": "switch",  "from": "B", "to": "C", "label": "$S$"},
    {"kind": "lamp",    "from": "C", "to": "D", "label": "$L$"},
    {"kind": "resistor","from": "D", "to": "A", "label": "$R=2\\,\\Omega$"}
  ]
}
```

`kind` 可选：`battery`、`battery2`、`resistor`、`lamp`、`switch`、`ammeter`、`voltmeter`、`capacitor`、`rheostat`、`fuse`、`motor`、`wire`。节点度数 ≥3 会自动画接点圆点。直线布线，拐角靠节点坐标摆。

**受力 `force`**：角度单位是度，0° 向右、90° 向上，箭头长度按 `magnitude` 等比缩放。

```json
{
  "type": "force", "size": [4.8, 3.6], "ground": true,
  "body": {"w": 1.2, "h": 0.7, "label": "$m$"},
  "forces": [
    {"label": "$G$", "angle": -90, "magnitude": 5},
    {"label": "$N$", "angle": 90,  "magnitude": 5},
    {"label": "$F$", "angle": 0,   "magnitude": 3},
    {"label": "$f$", "angle": 180, "magnitude": 2, "color": "#b3261e"}
  ]
}
```

**斜面 `incline`**：`decompose: true` 会画重力的两个分力（虚线）。

```json
{"type":"incline","angle":30,"block_label":"$m$","decompose":true,"base_label":"$L$"}
```

**凸透镜 `optics`**：按焦距、物距、物高自动画三条特殊光线和像。

```json
{"type":"optics","focal":1.5,"object_distance":2.8,"object_height":1.0}
```

### 数学

**函数图 `plot`**：表达式支持 `+ - * / ^` 和 `sin cos tan sqrt exp log abs floor` 等，`^` 表示乘方。

**乘号可以不写**——`x^2-2x-3`、`2(x+1)`、`(x+1)(x-1)`、`3sin(x)` 都会被自动补成合法表达式，
并在结果里告诉你补了什么。但**字母挨字母有歧义，会直接报错**：`xy` 请写 `x*y`，`x2` 请写 `x**2` 或 `x*2`。

```json
{
  "type": "plot", "x": [-3, 4],
  "functions": [
    {"expr": "x^2-2x", "label": "$y=x^2-2x$", "color": "#b3261e"},
    {"expr": "2x-3",   "label": "$y=2x-3$",   "color": "#2f5f9e"}
  ],
  "points": [{"x": 1, "y": -1, "label": "$(1,-1)$", "label_offset": [0.12, -0.45]}],
  "legend": "auto", "ticks": true, "xstep": 1, "ystep": 2
}
```

| 字段 | 说明 |
|---|---|
| `x` / `y` | 范围 `[min, max]`；**`y` 省略时按函数值自动算并留 10% 余量**。也认 `xmin/xmax/ymin/ymax` 老写法 |
| `legend` | `auto`（默认，挑一个曲线不经过的角）\| `ur` \| `ul` \| `br` \| `bl` \| `none` |
| `ticks` | 是否画刻度，默认 `true` |
| `grid` | 是否画网格，默认 `true` |
| `xstep` / `ystep` | 刻度间隔 |
| `points[].label_offset` | 点标签相对点的偏移，默认 `[0.18, 0.22]`；`offset` 是同一个意思 |

**平面几何 `geometry`**：点名坐标 + 线段/多边形/圆/角/直角标记/等长刻度。

```json
{
  "type": "geometry",
  "points": {"A": [0,0], "B": [4,0], "C": [2,3.4]},
  "segments": [["A","B"],["B","C"],["C","A"]],
  "angles": [{"at":"A","from":"B","to":"C","label":"$60^\\circ$","r":0.7}],
  "ticks": [{"from":"A","to":"B","n":1},{"from":"B","to":"C","n":1}]
}
```

**数轴 `numberline`**：`intervals` 画区间，实心/空心端点用 `left_closed/right_closed`。

```json
{"type":"numberline","min":-2,"max":5,
 "points":[{"x":-1,"label":"$-1$"},{"x":2,"filled":false,"label":"$2$"}],
 "intervals":[{"from":-1,"to":2,"left_closed":true,"right_closed":false,"label":"$[-1,2)$"}]}
```

**韦恩图 `venn`**：2~3 个集合，`counts` 的键为 `Aonly`、`Bonly`、`AB`（三集合再加 `Conly`、`AC`、`BC`、`ABC`）。

```json
{"type":"venn","sets":[{"label":"A"},{"label":"B"}],"counts":{"Aonly":6,"AB":4,"Bonly":7}}
```

### 化学

**装置 `apparatus`**：把仪器按坐标摆好，`water: false` 可去掉液体。

`parts` 是**对象数组**，每项 `{"kind": 仪器名, "at": [x, y], "scale": 1.0}`。
只想快速摆一排时，可以整组用字符串简写（会从左到右自动排开）：

```json
{"type":"apparatus","parts":["beaker","funnel","alcohol_lamp"]}
```

```json
{
  "type": "apparatus",
  "parts": [
    {"kind":"beaker","at":[0,0],"scale":1.0},
    {"kind":"funnel","at":[0.9,1.05],"scale":0.8},
    {"kind":"alcohol_lamp","at":[-1.2,0],"scale":0.9}
  ],
  "labels": [{"text":"过滤装置","at":[-2.0,1.8],"size":10}],
  "notes": [{"text":"冷凝水","at":[2.0,1.2],"target":[0.9,0.4]}]
}
```

`kind` 可选：`beaker`、`flask`、`round_flask`、`test_tube`、`gas_jar`、`trough`、`funnel`、`alcohol_lamp`、`iron_stand`、`condenser`、`thermometer`、`tube`（`tube` 用 `points` 画任意导管折线）。
`notes` 是带引线的标注对象数组（`text` + `at` 文字位置 + `target` 指向）。

**分子结构 `molecule`**：给 SMILES，RDKit 出结构式。输出 `.svg` 或 `.png`。

```json
{"type":"molecule","smiles":"CCO","label":"乙醇","pixels":[700,450]}
```

### 生物

**细胞 `cell`**：`kind` 为 `plant` 或 `animal`；`notes` 追加自定义标注，会自动避开内置标签。

- `notes` 是**对象数组** `[{"text", "at", "target"}]`，不是开关；
- 想全部自己标：`"show_builtin_labels": false`；
- 不知道往哪放：先 `--dry-run`，它会打印内置标签坐标（也支持工具参数 `dry_run: true`）。

```json
{"type":"cell","kind":"plant","notes":[{"text":"中心体","target":[0.2,0.3],"at":[2.4,0.2]}]}
```

**流程 `flow`**：横向/纵向步骤框。

```json
{"type":"flow","steps":["光反应","ATP、NADPH","暗反应"],"layout":"horizontal"}
```

### 语文

**田字格 `grid`**：`chars` 为要练的字，`pinyin` 与之一一对应；`style` 用 `tian` 或 `mi`（米字格）。

```json
{"type":"grid","chars":"春江花月夜","pinyin":["chūn","jiāng","huā","yuè","yè"],"cols":5}
```

## 排错

| 现象 | 处理 |
|---|---|
| 箭头/标签被裁掉 | 调大 `size`，或把坐标范围拉开；力的 `magnitude` 不要差太多倍 |
| 图像空白 | 检查 `type` 拼写；用 `doctor` 看模板名 |
| 中文成方框 | Windows 需有 SimSun/SimHei；`assets/base.py` 里可改字体栈 |
| 分子式报 SMILES 错 | 检查括号/原子符号；先用 `CCO` 试通 |
| 电路元件方向反了 | 把 `from`/`to` 对调；电池长线是正极 |
