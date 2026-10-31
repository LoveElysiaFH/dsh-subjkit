# -*- coding: utf-8 -*-
"""函数表达式的解析：把「人写的数学」变成「能算的 Python」。

学生写 `x^2-2x-3`，Python 要的是 `x**2-2*x-3`。这里做两件事：

1. **能猜就猜**：`2x`、`2(x+1)`、`x(x+1)`、`(x+1)(x-1)`、`3sin(x)` 里的乘号自动补上，
   并把补了什么告诉调用方（不静默改）；
2. **猜不动就报清楚**：`xy` 到底是 x·y 还是变量名？`x2` 是 x² 还是 x·2？
   这种一律报错，并给出两种改法的例子——**绝不把 SyntaxError 丢给使用者**。

安全：只允许 `x` + 白名单函数 + 四则运算/乘方/比较，用 AST 白名单校验，`eval` 时禁用 `__builtins__`。
"""
from __future__ import annotations

import ast
import re

import numpy as np

FUNCS = {
    "sin": np.sin, "cos": np.cos, "tan": np.tan,
    "arcsin": np.arcsin, "arccos": np.arccos, "arctan": np.arctan,
    "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
    "exp": np.exp, "log": np.log, "ln": np.log, "log10": np.log10, "log2": np.log2,
    "sqrt": np.sqrt, "abs": np.abs, "floor": np.floor, "ceil": np.ceil,
    "sign": np.sign, "pi": np.pi, "e": np.e,
}

# 名字长度 ≥2 的按「函数」处理，后面紧跟 `(` 时**不**补乘号（sin( 不是 sin*( ）
FUNC_NAMES = {k for k in FUNCS if len(k) > 1}
VARIABLES = {"x"}

_ALLOWED = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Constant,
    ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
    ast.USub, ast.UAdd, ast.Lt, ast.Gt, ast.LtE, ast.GtE, ast.Eq, ast.NotEq,
)

_NUM = re.compile(r"\d+(?:\.\d+)?")
_ID = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


class ExprError(ValueError):
    """表达式不合法；消息已写成中文，附建议写法。"""


def tokenize(expr: str) -> list[tuple[str, str]]:
    toks: list[tuple[str, str]] = []
    i, n = 0, len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
            continue
        if expr.startswith("**", i):
            toks.append(("op", "**"))
            i += 2
            continue
        m = _NUM.match(expr, i)
        if m:
            toks.append(("num", m.group()))
            i = m.end()
            continue
        m = _ID.match(expr, i)
        if m:
            toks.append(("id", m.group()))
            i = m.end()
            continue
        toks.append(("op", c))
        i += 1
    return toks


def _looks_like_value(kind: str, text: str) -> bool:
    return kind in ("num", "id") or (kind == "op" and text == ")")


def normalize_expr(expr: str) -> tuple[str, list[str]]:
    """补乘号并检查名字；返回 (可直接 parse 的表达式, 改动说明)。

    Raises:
        ExprError: 名字不在白名单、或写法有歧义。
    """
    src = expr.strip()
    if not src:
        raise ExprError("表达式是空的")

    text = src.replace("^", "**")
    toks = tokenize(text)
    if not toks:
        raise ExprError(f"表达式「{src}」里没有可计算的内容")

    # 先查名字：一次把可疑的写法都指出来，比逐个报错省事
    for kind, word in toks:
        if kind != "id" or word in FUNCS or word in VARIABLES:
            continue
        if len(word) == 1:
            raise ExprError(
                f"不支持的符号「{word}」：目前只认变量 x"
                f"{'（想用希腊字母请用文字标签，别写进表达式）' if word.isalpha() else ''}"
                f"\n  例：把 {word} 换成 x，或整条表达式改成用 x 写的"
            )
        if word[0] == "x" and word[1:].isdigit():
            raise ExprError(
                f"「{word}」有歧义：是 x² 还是 x 乘 {word[1:]}？"
                f"\n  写平方：x**2（或 x^2）\n  写乘法：x*{word[1:]}"
            )
        if all(ch.isalpha() for ch in word):
            raise ExprError(
                f"「{word}」有歧义：是想写字母相乘吗？"
                f"\n  字母相乘要显式写乘号：{'*'.join(word)}\n"
                f"  如果这是一个函数，可用：{', '.join(sorted(FUNC_NAMES))}"
            )
        raise ExprError(f"不支持的符号「{word}」；可用变量只有 x，可用函数：{', '.join(sorted(FUNC_NAMES))}")

    out: list[str] = []
    fixes: list[str] = []
    prev: tuple[str, str] | None = None

    for kind, word in toks:
        if prev is not None:
            pk, ptext = prev
            left_is_value = _looks_like_value(pk, ptext)
            right_is_value = kind in ("num", "id") or (kind == "op" and word == "(")
            left_is_func = pk == "id" and ptext in FUNC_NAMES
            if left_is_value and right_is_value and not left_is_func:
                insert = False
                if pk == "op" and ptext == ")":
                    insert = kind in ("num", "id") or word == "("
                elif pk == "num":
                    insert = kind == "id" or word == "("
                elif pk == "id":
                    insert = word == "("
                if insert:
                    out.append("*")
                    fixes.append(f"{ptext}{word}")
        out.append(word)
        prev = (kind, word)

    result = "".join(out)
    return result, fixes


def compile_expr(expr: str):
    """解析成 code 对象；语法错误统一转成中文 ExprError。"""
    normalized, fixes = normalize_expr(expr)
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as e:
        hint = ""
        if re.search(r"[+\-*/]\s*[+\-*/]", normalized):
            hint = "\n  看起来有两个运算符连在一起，检查一下括号和符号"
        if normalized.count("(") != normalized.count(")"):
            hint += "\n  括号不配对：'(' 与 ')' 数量不同"
        raise ExprError(
            f"表达式「{expr}」解析失败（{e.msg}）"
            f"\n  补完乘号后是：{normalized}{hint}"
        ) from e
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id not in VARIABLES and node.id not in FUNCS:
                raise ExprError(f"不支持的符号：{node.id}")
        elif isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and node.func.id in FUNCS):
                raise ExprError(f"只允许使用这些函数：{', '.join(sorted(FUNC_NAMES))}")
        elif not isinstance(node, _ALLOWED):
            raise ExprError(f"表达式里不允许 {type(node).__name__}")
    return compile(tree, "<expr>", "eval")


def make_fn(expr: str):
    code = compile_expr(expr)

    def fn(x):
        with np.errstate(all="ignore"):
            return eval(code, {"__builtins__": {}}, {"x": x, **FUNCS})

    return fn


def describe_expr(expr: str) -> tuple[str, list[str]]:
    """给 dry-run / 报错用：返回（归一化后的表达式, 改动说明）。"""
    normalized, fixes = normalize_expr(expr)
    return normalized, ([f"已自动补乘号：{f}" for f in fixes] if fixes else [])
