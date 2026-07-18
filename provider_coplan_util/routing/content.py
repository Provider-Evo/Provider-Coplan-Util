"""content 模块 — Provider 适配器层。

职责：
    作为 Provider-Evo 项目标准模块，提供 content 能力。

本文件为 Provider-Evo 项目标准模块；保持单文件 200-400 行。
修改指引参见文件末尾的"本模块对外契约"章节（共 20 条）。
"""


from __future__ import annotations

from typing import Any, Dict, List

DEFAULT_HERO_TAGLINE = "高品质 AI API 代理服务，稳定、快速、可信赖。聚合多平台多模型，按策略组智能调度。"
DEFAULT_AGENTS_TITLE = "支持的 AI Agent 与客户端"
DEFAULT_ADVANTAGES_TITLE = "核心优势"
DEFAULT_PRICING_TITLE = "选择你的方案"
DEFAULT_FAQ_TITLE = "常见问题"
DEFAULT_CONTACT_HINT = "需要定制方案或有问题？"
DEFAULT_ADMIN_CONTACT = "请联系管理员"

DEFAULT_AGENTS: List[Dict[str, str]] = [
    {"name": "OpenCode", "logo_url": "https://opencode.ai/docs/_astro/logo-light.B0yzR0O5.svg"},
    {"name": "Claude Code", "logo_url": "https://i-blog.csdnimg.cn/img_convert/f65bd32bc5434195f1c5b05e8fabbac3.png"},
    {"name": "Cursor", "logo_url": "https://filecdn.minimax.chat/public/3dcf5110-d72b-4498-88e6-60229b893aaa.png"},
    {"name": "Cline", "logo_url": "https://filecdn.minimax.chat/public/393bc223-b874-4874-b73b-d34c437660be.png"},
    {"name": "Roo Code", "logo_url": "https://filecdn.minimax.chat/public/077e6a20-e872-4766-8498-8247ddf2b679.png"},
    {"name": "Codex CLI", "logo_url": "https://filecdn.minimax.chat/public/b96de335-8f83-4f90-85ea-33c4c8adaf70.png"},
]

DEFAULT_ADVANTAGES: List[Dict[str, str]] = [
    {
        "icon": "⚡",
        "title": "多平台智能路由",
        "description": "聚合 Provider 已接入平台插件，按策略组在 Ollama、OpenRouter、DeepSeek、Zen 等来源间调度。",
        "tag": "策略组调度",
    },
    {
        "icon": "🔧",
        "title": "开放协议兼容",
        "description": "兼容 OpenAI、Anthropic 等主流 API 形态，可对接各类 Coding Agent 与自研客户端。",
        "tag": "OpenAI / Anthropic",
    },
    {
        "icon": "🧩",
        "title": "插件化扩展",
        "description": "平台能力由 Provider-*-Adapter 插件提供，启用即可纳入 Coplan 策略市场与密钥池。",
        "tag": "Provider-Evo 生态",
    },
    {
        "icon": "✨",
        "title": "密钥与配额治理",
        "description": "Entropy 前缀密钥、策略模板与市场方案统一管理，支持独立门户与主站双入口。",
        "tag": "sk-ent-*",
    },
]

DEFAULT_FAQS: List[Dict[str, str]] = [
    {
        "q": "如何获取 API 密钥？",
        "a": "使用管理员配置的账号登录后，在控制台「API 密钥」页为策略组生成 sk-ent-* 密钥；也可由管理员在后台创建策略组并签发密钥。",
    },
    {
        "q": "支持哪些 AI 工具与客户端？",
        "a": "兼容 OpenCode、Claude Code、Cursor、Cline 等 Coding Agent，以及任何支持 OpenAI/Anthropic 兼容协议的 HTTP 客户端。",
    },
    {
        "q": "支持哪些模型与平台？",
        "a": "取决于 Provider 网关已启用的平台插件（如 Ollama 本地、Qwen、Zen、ChatMoe、OpenRouter、DeepSeek 等）。策略市场模板预置多源模型组合，可按场景选用。",
    },
    {
        "q": "策略组与市场模板有何区别？",
        "a": "策略组定义路由规范（aliases / default）；套餐（Free / Pro / Ultra）是面向用户的配额与定价方案，由管理员开通后绑定策略组使用。",
    },
    {
        "q": "如何定义策略组路由？",
        "a": "在插件目录 strategies/*.py 中定义 STRATEGY_GROUPS 列表（Python dict），重载 Coplan 插件后自动同步；规范字段见 GET /v1/coplan/strategy-spec。",
    },
    {
        "q": "独立端口与主站 /coplan 有何不同？",
        "a": "独立端口（默认 8787）提供精简 CodingPlan 门户；主站路径 /coplan 嵌入同一套 UI 与 API，便于与 Provider WebUI 共存。",
    },
    {
        "q": "API 密钥如何保障安全？",
        "a": "密钥仅在创建时完整展示一次，支持按策略组撤销；请勿将 sk-ent-* 密钥提交到公开仓库或日志。",
    },
]

DEFAULT_PLATFORMS: List[str] = [
    "Ollama",
    "Qwen",
    "Zen",
    "ChatMoe",
    "OpenRouter",
    "DeepSeek",
    "EdgeTTS",
    "OpenAI FM",
]


def build_public_payload(
    cfg: Any,
    settings: Dict[str, Any],
    market_templates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """组装 /v1/coplan/public 响应。"""
    admin_contact = str(settings.get("admin_contact") or cfg.admin_contact or DEFAULT_ADMIN_CONTACT)
    return {
        "brand": "entropy",
        "brand_title": "Entropy",
        "hero_tagline": cfg.hero_tagline,
        "subtitle": cfg.subtitle,
        "agents_title": cfg.agents_title,
        "advantages_title": cfg.advantages_title,
        "pricing_title": cfg.pricing_title,
        "faq_title": cfg.faq_title,
        "contact_hint": cfg.contact_hint,
        "admin_contact": admin_contact,
        "agents": cfg.agents or DEFAULT_AGENTS,
        "advantages": cfg.advantages or DEFAULT_ADVANTAGES,
        "faqs": cfg.faqs or DEFAULT_FAQS,
        "platforms": cfg.platforms or DEFAULT_PLATFORMS,
        "market_templates": market_templates,
        "standalone_enabled": cfg.standalone_enabled,
        "standalone_host": cfg.standalone_host,
        "standalone_port": cfg.standalone_port,
    }
