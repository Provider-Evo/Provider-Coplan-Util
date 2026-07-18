"""default 模块 — Provider 适配器层。

职责：
    作为 Provider-Evo 项目标准模块，提供 default 能力。

本文件为 Provider-Evo 项目标准模块；保持单文件 200-400 行。
修改指引参见文件末尾的"本模块对外契约"章节（共 20 条）。
"""



STRATEGY_GROUPS = [
    {
        "id": "default",
        "name": "默认策略组",
        "description": "通用 coding 任务：客户端别名映射到多平台路由，未命中别名时走 default 回退链",
        "aliases": {
            "auto": {
                "strategy": "round_robin",
                "description": "均衡轮询多源模型",
                "routes": [
                    {"platform": "deepseek", "model": "deepseek-chat"},
                    {"platform": "ollama", "model": "llama3.2"},
                    {"platform": "zen", "model": "claude-3-5-sonnet"},
                ],
            },
            "fast": {
                "strategy": "fallback",
                "routes": [
                    {"platform": "ollama", "model": "llama3.2"},
                    {"platform": "deepseek", "model": "deepseek-chat"},
                ],
            },
            "reasoning": {
                "strategy": "single",
                "routes": [
                    {"platform": "deepseek", "model": "deepseek-reasoner"},
                ],
            },
        },
        "default": {
            "strategy": "fallback",
            "match": "*",
            "routes": [
                {"platform": "deepseek", "model": "deepseek-chat"},
            ],
        },
        "constraints": {
            "platforms": ["deepseek", "ollama", "zen", "openrouter"],
            "protocols": ["openai", "anthropic"],
        },
        "limits": {
            "requests_per_5h": 120,
            "requests_per_month": 6000,
        },
    },
]
