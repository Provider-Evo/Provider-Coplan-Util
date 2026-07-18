"""strat_sbox 模块 — Provider 适配器层。

职责：
    作为 Provider-Evo 项目标准模块，提供 strat_sbox 能力。

本文件为 Provider-Evo 项目标准模块；保持单文件 200-400 行。
修改指引参见文件末尾的"本模块对外契约"章节（共 20 条）。
"""


from __future__ import annotations

import ast
from typing import Any, Dict, Tuple

__all__ = ["MAX_STRATEGY_SOURCE_BYTES", "validate_and_extract_strategy_group"]

MAX_STRATEGY_SOURCE_BYTES = 64 * 1024
_ENTRY_NAME = "STRATEGY_GROUP"


def _reject(message: str) -> None:
    raise ValueError(message)


def _validate_literal_expr(node: ast.AST) -> None:
    if isinstance(node, ast.Constant):
        return
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values):
            if key is not None and not isinstance(key, ast.Constant):
                _reject("策略组 dict 的键须为字面量")
            if isinstance(key, ast.Constant) and not isinstance(key.value, str):
                _reject("策略组 dict 的键须为字符串字面量")
            _validate_literal_expr(value)
        return
    if isinstance(node, ast.List):
        for item in node.elts:
            _validate_literal_expr(item)
        return
    if isinstance(node, ast.Tuple):
        for item in node.elts:
            _validate_literal_expr(item)
        return
    if isinstance(node, (ast.UnaryOp, ast.BinOp)):
        _reject("策略组定义中不允许运算表达式")
    _reject(f"不允许的表达式类型: {type(node).__name__}")


def validate_and_extract_strategy_group(source: str) -> Dict[str, Any]:
    """解析并提取 STRATEGY_GROUP 字面量 dict；禁止 import、函数、调用等。"""
    text = source.strip()
    if not text:
        _reject("策略代码不能为空")
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_STRATEGY_SOURCE_BYTES:
        _reject(f"策略代码超过 {MAX_STRATEGY_SOURCE_BYTES} 字节上限")

    try:
        module = ast.parse(text, mode="exec")
    except SyntaxError as exc:
        _reject(f"Python 语法错误: {exc.msg}")

    assign_node: ast.Assign | None = None
    for stmt in module.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
            continue
        if isinstance(stmt, ast.Assign):
            if assign_node is not None:
                _reject("仅允许一个 STRATEGY_GROUP 赋值")
            assign_node = stmt
            continue
        _reject(f"不允许的顶层语句: {type(stmt).__name__}")

    if assign_node is None:
        _reject(f"代码须包含 {_ENTRY_NAME} = {{...}} 赋值")

    target_names = [
        target.id
        for target in assign_node.targets
        if isinstance(target, ast.Name)
    ]
    if target_names != [_ENTRY_NAME]:
        _reject(f"仅允许赋值给 {_ENTRY_NAME}")

    _validate_literal_expr(assign_node.value)
    try:
        raw = ast.literal_eval(assign_node.value)
    except ValueError as exc:
        _reject(f"STRATEGY_GROUP 须为字面量 dict: {exc}")
    if not isinstance(raw, dict):
        _reject("STRATEGY_GROUP 必须为 dict")
    return raw


def compile_check_summary(source: str) -> Tuple[Dict[str, Any], str]:
    """校验并返回 (spec_dict, status_message)。"""
    raw = validate_and_extract_strategy_group(source)
    return raw, "ok"
