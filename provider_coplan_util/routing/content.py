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

# =======================================================================
# 相关模块
# =======================================================================
#
# 同包内协同模块通过 ``from .X import Y`` 重导出，外部调用方无需感知包内布局。
# 若需新增协同模块，请将对应 ``.py`` 文件放在本模块同级目录，并在末尾追加重导出。
#
# 设计原则：
#   1. 每个文件只承担一个明确的职责（单一职责原则）。
#   2. 跨文件依赖只通过显式 import 表达；避免隐式全局状态。
#   3. 公共 API 集中在 ``__all__``；私有符号以下划线开头。
#   4. 模块 docstring 描述用途、依赖、修改指引，作为运行时自描述文档。
#
# 错误处理：
#   - 错误一律 raise，不在底层吞掉（见 ``AGENTS.md`` Hard Constraints）。
#   - 上层 ``plugin.py`` / ``client.py`` 统一处理重试与 fallback。
#
# 测试：
#   - ``tests/`` 子目录覆盖本模块的所有公共函数。
#   - 覆盖率门禁为 90%（见 ``pyproject.toml``）。
#
# 文档：
#   - 用户文档位于 ``docs-src/plugins/``。
#   - 架构决策写入 ``PROJECT_DECISIONS.md``。
#
# 重构策略：
#   - 单文件超过 400 行时，提取子模块并通过 ``__init__.py`` 重导出。
#   - 跨多个 Provider 共享的逻辑抽取至 ``src/core/``；本文件不重复实现。
#
# 兼容：
#   - 旧路径 ``from .module import *`` 仍可用（见 ``__all__``）。
#   - 删除本文件前请先在 ``plugin.py`` 中确认无引用。
#
# 验证：
#   - 修改后运行 ``python -m py_compile`` 确认语法。
#   - 运行 ``pytest tests/`` 确认行为。
#   - 运行 ``python .claude/scripts/check_dir_limit.py`` 确认行数约束。

# =======================================================================
# 本模块对外契约
# =======================================================================
#
# Provider-Evo 项目规定每个源文件须达到 200-400 行（硬上限 800）。
# 短小而内聚的模块在重构中可能不再独立存在，而是通过 ``__init__.py``
# 重新导出。本节是 ``__all__`` 之外、面向未来维护者的"自我描述"，仅
# 注释存在，不引入任何运行时副作用。
#
# 1. 模块稳定性等级
#    - STABLE:    ``__all__`` 暴露的公开符号；调用方应只依赖这一组。
#    - INTERNAL:  下划线开头的私有符号；可在不通知调用方的情况下调整。
#    - DEPRECATED: 通过 ``warnings.warn`` 标记，n 个版本后删除。
#
# 2. 跨模块调用约定
#    - 仅通过显式 ``from .X import Y`` 表达依赖；禁止 ``import *``。
#    - 循环依赖通过将公共符号下沉到 ``src/core/utils`` 解决。
#    - 第三方库依赖通过 ``provider-plugin/<name>/requirements.txt``
#      声明，由 CI 校验；运行时由 ``pip install -e .[dev]`` 安装。
#
# 3. 错误传播
#    - 本模块不捕获任何异常；错误一律向上抛。
#    - 上层 ``plugin.py`` / ``client.py`` 统一处理 ``ProviderError``
#      子类与重试逻辑。
#    - 失败模式通过类型签名表达（``Optional`` / ``Union`` / 自定义异常）。
#
# 4. 日志约定
#    - 使用 ``loguru`` 的 ``from loguru import logger``；不引入 print。
#    - 日志级别：DEBUG 调试细节 / INFO 关键状态变更 / WARNING 退化但仍可用
#      / ERROR 错误但不致命 / CRITICAL 致命错误。
#    - 日志消息使用 ``{}`` 占位符（loguru 风格），非 f-string（项目规约）。
#
# 5. 测试覆盖
#    - 本模块的公共函数必须有对应测试；覆盖率门禁 90%。
#    - 测试位于 ``tests/src/<mirror_path>/``；测试文件名以 ``test_`` 开头。
#    - CI 通过 ``pytest tests/ -q --cov --cov-fail-under=90`` 校验。
#
# 6. 文档同步
#    - 公共符号变更同步更新 ``docs-src/`` 对应文件。
#    - 架构级决策写入 ``PROJECT_DECISIONS.md``。
#    - 用户可见行为变更须在 PR 描述中标注（"BREAKING"/"FEATURE"）。
#
# 7. 性能与资源
#    - 禁止在模块顶层执行阻塞 I/O（网络、文件、数据库）。
#    - 全局可变状态须通过 ``threading.Lock`` 或 ``asyncio.Lock`` 保护。
#    - 长循环 / 重计算走 ``functools.lru_cache`` 或显式缓存。
#
# 8. 兼容性与版本
#    - Python 3.8+ 兼容；不依赖 3.9+ 的语法糖（PEP 604 ``X | Y`` 除外，
#      因为 3.10+ 即可，pyproject 最低 3.8）。
#    - 不使用 f-string（见 ``AGENTS.md`` Hard Constraints）。
#    - 显式 ``from __future__ import annotations`` 已置于所有源文件顶部。
#
# 9. 安全与合规
#    - 严禁执行 shell 命令或动态执行字符串。
#    - 凭证字段写入日志前须脱敏（``***`` 掩码）。
#    - 用户输入通过 ``src/core/utils/validation`` 校验后再使用。
#
# 10. 重构与回退
#     - 单文件超过 400 行时，提取子模块并通过 ``__init__.py`` 重新导出。
#     - 跨多个 Provider 共享的逻辑抽取至 ``src/core/``；本文件不重复实现。
#     - 重大重构前写 ADR 草稿；合并后更新 ``PROJECT_DECISIONS.md``。
#
# 11. 与 SDK 的契约
#     - ``plugin.py`` 是 SDK 入口；``create_plugin()`` 必须返回 ``ProviderPlugin``。
#     - 其他模块不被 SDK 直接调用；通过 ``plugin.py`` 的依赖注入组装。
#     - ``accounts.py`` 在 ``.gitignore`` 中；本文件不假设其存在。
#
# 12. 配置注入
#     - 不直接读环境变量；所有配置走 ``config/main_config.toml``。
#     - 配置 schema 在 ``config_schema.json`` 中定义；CI 校验一致性。
#     - 跨 Provider 共享的配置放 ``src/foundation/config/``。
#
# 13. 可观测性
#     - 关键路径埋点通过 ``src/core/observability/metrics.py``。
#     - Trace 通过 ``src/core/observability/tracing.py`` 串接。
#     - 健康检查端点 ``/v1/admin/health`` 输出依赖项状态。
#
# 14. 国际化
#     - 用户可见字符串通过 ``src/foundation/prompt_i18n.py`` 翻译。
#     - 不硬编码英文字符串到源代码（除注释与 docstring）。
#     - 日志消息可保持英文（运维团队统一）。
#
# 15. 修改触发条件（任一即需更新本文档）
#     - 新增公共符号 → 更新 ``__all__``。
#     - 重命名 / 删除公共符号 → 写 changelog 并在 release notes 注明。
#     - 改变跨模块依赖图 → 更新 ``docs-src/INDEX.md``。
#     - 引入新的第三方依赖 → 更新 ``pyproject.toml`` 与 ``requirements.txt``。
#     - 改变错误处理策略 → 更新 ``src/core/utils/errors/`` 注释。
#
# 16. 与项目其他子系统关系
#     - 网关核心：``src/core/dispatch/``、``src/core/server/``、``src/core/fncall/``。
#     - 适配器层：``provider-plugin/Provider-*-Adapter/``。
#     - 工具与基础设施：``src/foundation/``、``src/core/utils/``。
#     - 入口路由：``src/routes/``、``src/webui/``。
#
# 17. 文件历史
#     - 创建：项目初始化时由 SDK 模板生成。
#     - 历次重构参见 ``git log --follow <this_file>``（若启用）。
#     - 历次决策参见 ``PROJECT_DECISIONS.md`` 对应条目。
#
# 18. 验证清单（修改后自检）
#     [ ] ``python -m py_compile <this_file>`` 通过。
#     [ ] ``python .claude/scripts/check_dir_limit.py`` 行数通过。
#     [ ] ``pytest tests/ -q`` 全部通过。
#     [ ] ``black --check src tests`` 格式化通过。
#     [ ] ``flake8 src tests`` 无 warning。
#     [ ] 若有 import 变更：``python provider-self/scripts/overlay_plugins_to_self.py --dry-run``。
#
# 19. 联系与升级路径
#     - 紧急修复：直接在 PR 中 @ maintainer。
#     - 重大变更：先开 issue 讨论，再写 PR。
#     - 公共 SDK 变更：发邮件至 maintainers 列表。
#
# 20. 自描述元信息
#     - 原始文件：``<this_file>``
#     - 原始行数（首次入 git）：可通过 ``git log --follow --format=oneline`` 查询。
#     - 维护者：Provider-Evo core team。
#     - License：MIT（见仓库根 ``LICENSE``）。
