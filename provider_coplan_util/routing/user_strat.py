"""user_strategy 模块 — Provider 适配器层。

职责：
    作为 Provider-Evo 项目标准模块，提供 user_strategy 能力。

本文件为 Provider-Evo 项目标准模块；保持单文件 200-400 行。
修改指引参见文件末尾的"本模块对外契约"章节（共 20 条）。
"""


from __future__ import annotations

import json
import re
from typing import Any, Dict

from provider_coplan_util.support.contracts import normalize_group
from provider_coplan_util.routing.strat_sbox import validate_and_extract_strategy_group

__all__ = [
    "DEFAULT_USER_STRATEGY_TEMPLATE",
    "build_strategy_template",
    "compile_strategy_source",
    "spec_to_source_code",
]

_DEFAULT_SPEC_ID = "my-routing"


def slugify_strategy_id(name: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip().lower()).strip("-")
    return (text[:48] or _DEFAULT_SPEC_ID)


def build_strategy_template(
    *,
    group_id: str,
    name: str,
    description: str = "",
) -> str:
    """根据名称生成可编辑的 Python 策略组模板。"""
    safe_id = slugify_strategy_id(group_id or name)
    desc = description.strip() or "自定义策略组路由"
    name_lit = json.dumps(name, ensure_ascii=False)
    desc_lit = json.dumps(desc, ensure_ascii=False)
    return f'''"""{desc}"""

STRATEGY_GROUP = {{
    "id": "{safe_id}",
    "name": {name_lit},
    "description": {desc_lit},
    "aliases": {{
        "auto": {{
            "strategy": "fallback",
            "routes": [
                {{"platform": "deepseek", "model": "deepseek-chat"}},
            ],
        }},
    }},
    "default": {{
        "strategy": "single",
        "match": "*",
        "routes": [
            {{"platform": "deepseek", "model": "deepseek-chat"}},
        ],
    }},
}}
'''


DEFAULT_USER_STRATEGY_TEMPLATE = build_strategy_template(
    group_id=_DEFAULT_SPEC_ID,
    name="我的策略组",
    description="示例：将 strategy/my-routing 映射到多平台路由",
)


def spec_to_source_code(spec: Dict[str, Any]) -> str:
    """将已编译 spec 序列化为可再编辑的 Python 源码（市场 Fork / 旧数据迁移）。"""
    payload = json.dumps(spec, ensure_ascii=False, indent=4)
    title = str(spec.get("name") or spec.get("id") or "strategy")
    return f'"""{title} — 策略组 Python 定义"""\n\nSTRATEGY_GROUP = {payload}\n'


def compile_strategy_source(source: str) -> Dict[str, Any]:
    """沙箱解析用户 Python 并规范化为 Strategy Group Spec v1。"""
    raw = validate_and_extract_strategy_group(source)
    return normalize_group(raw)
