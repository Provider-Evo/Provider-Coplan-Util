"""Coplan 插件配置（config.toml）、品牌与 Key 规范、默认套餐、模型种子数据。"""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from provider_coplan_util.routing.content import (
    DEFAULT_ADMIN_CONTACT,
    DEFAULT_ADVANTAGES,
    DEFAULT_ADVANTAGES_TITLE,
    DEFAULT_AGENTS,
    DEFAULT_AGENTS_TITLE,
    DEFAULT_CONTACT_HINT,
    DEFAULT_FAQ_TITLE,
    DEFAULT_FAQS,
    DEFAULT_HERO_TAGLINE,
    DEFAULT_PLATFORMS,
    DEFAULT_PRICING_TITLE,
)

try:
    from src.foundation.logger import get_logger
except ImportError:
    import logging

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

DEFAULT_STANDALONE_PORT = 8787
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "changeme"

__all__ = [
    "CoplanConfig",
    "DEFAULT_ADMIN_PASSWORD",
    "DEFAULT_ADMIN_USERNAME",
    "DEFAULT_HERO_TAGLINE",
    "DEFAULT_STANDALONE_PORT",
    "load_coplan_config",
]

logger = get_logger(__name__)


@dataclass
class CoplanConfig:
    hero_tagline: str
    subtitle: str
    agents_title: str
    advantages_title: str
    pricing_title: str
    faq_title: str
    contact_hint: str
    admin_contact: str
    standalone_enabled: bool
    standalone_host: str
    standalone_port: int
    standalone_access_log: bool
    standalone_startup_force_kill_port: bool
    admin_username: str
    admin_password: str
    strategies_dir: str
    agents: List[Dict[str, str]] = field(default_factory=list)
    advantages: List[Dict[str, str]] = field(default_factory=list)
    faqs: List[Dict[str, str]] = field(default_factory=list)
    platforms: List[str] = field(default_factory=list)

    def as_public_dict(self) -> Dict[str, Any]:
        return {
            "hero_tagline": self.hero_tagline,
            "standalone_enabled": self.standalone_enabled,
            "standalone_host": self.standalone_host,
            "standalone_port": self.standalone_port,
        }


def _section(data: Any, key: str) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    section = data.get(key, {})
    return section if isinstance(section, dict) else {}


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_json_list(path: Path, key: str) -> Optional[List[Any]]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get(key), list):
            return data[key]
    except Exception:
        return None
    return None


def _defaults() -> CoplanConfig:
    return CoplanConfig(
        hero_tagline=DEFAULT_HERO_TAGLINE,
        subtitle="Entropy 代码计划",
        agents_title=DEFAULT_AGENTS_TITLE,
        advantages_title=DEFAULT_ADVANTAGES_TITLE,
        pricing_title=DEFAULT_PRICING_TITLE,
        faq_title=DEFAULT_FAQ_TITLE,
        contact_hint=DEFAULT_CONTACT_HINT,
        admin_contact=DEFAULT_ADMIN_CONTACT,
        standalone_enabled=True,
        standalone_host="127.0.0.1",
        standalone_port=DEFAULT_STANDALONE_PORT,
        standalone_access_log=False,
        standalone_startup_force_kill_port=True,
        admin_username=DEFAULT_ADMIN_USERNAME,
        admin_password=DEFAULT_ADMIN_PASSWORD,
        strategies_dir=".",
        agents=list(DEFAULT_AGENTS),
        advantages=list(DEFAULT_ADVANTAGES),
        faqs=list(DEFAULT_FAQS),
        platforms=list(DEFAULT_PLATFORMS),
    )


def _apply_toml_sections(cfg: CoplanConfig, raw: Any) -> Dict[str, Any]:
    """把 [coplan]/[server]/[admin] 三个 TOML section 的值套用到 cfg 上，返回 coplan section。"""
    coplan = _section(raw, "coplan")
    server = _section(raw, "server")
    admin = _section(raw, "admin")

    cfg.hero_tagline = str(coplan.get("hero_tagline") or cfg.hero_tagline).strip() or DEFAULT_HERO_TAGLINE
    cfg.subtitle = str(coplan.get("subtitle") or cfg.subtitle).strip()
    cfg.agents_title = str(coplan.get("agents_title") or cfg.agents_title).strip()
    cfg.advantages_title = str(coplan.get("advantages_title") or cfg.advantages_title).strip()
    cfg.pricing_title = str(coplan.get("pricing_title") or cfg.pricing_title).strip()
    cfg.faq_title = str(coplan.get("faq_title") or cfg.faq_title).strip()
    cfg.contact_hint = str(coplan.get("contact_hint") or cfg.contact_hint).strip()
    cfg.admin_contact = str(coplan.get("admin_contact") or cfg.admin_contact).strip()
    cfg.standalone_enabled = _as_bool(server.get("enabled"), cfg.standalone_enabled)
    cfg.standalone_host = str(server.get("host") or cfg.standalone_host).strip() or "127.0.0.1"
    cfg.standalone_port = _as_int(server.get("port"), cfg.standalone_port)
    cfg.standalone_access_log = _as_bool(server.get("access_log"), cfg.standalone_access_log)
    cfg.standalone_startup_force_kill_port = _as_bool(server.get("startup_force_kill_port"), cfg.standalone_startup_force_kill_port)
    cfg.admin_username = str(admin.get("username") or cfg.admin_username).strip() or DEFAULT_ADMIN_USERNAME
    cfg.admin_password = str(admin.get("password") or cfg.admin_password)
    cfg.strategies_dir = str(coplan.get("strategies_dir") or cfg.strategies_dir).strip() or "."
    return coplan


def _apply_content_file(cfg: CoplanConfig, plugin_dir: Path, coplan: Dict[str, Any]) -> None:
    """按 [coplan].content_file 指向的 JSON 文件覆盖 agents/advantages/faqs/platforms。"""
    content_file = str(coplan.get("content_file") or "").strip()
    if not content_file:
        return
    content_path = plugin_dir / content_file
    agents = _load_json_list(content_path, "agents")
    advantages = _load_json_list(content_path, "advantages")
    faqs = _load_json_list(content_path, "faqs")
    platforms = _load_json_list(content_path, "platforms")
    if agents:
        cfg.agents = agents
    if advantages:
        cfg.advantages = advantages
    if faqs:
        cfg.faqs = faqs
    if platforms and all(isinstance(p, str) for p in platforms):
        cfg.platforms = platforms


def load_coplan_config(plugin_dir: Path) -> CoplanConfig:
    """读取插件目录下 config.toml；缺失时使用默认值。"""
    cfg = _defaults()
    path = plugin_dir / "config.toml"
    if not path.is_file():
        return cfg
    try:
        import tomlkit

        raw = tomlkit.loads(path.read_text(encoding="utf-8"))
        coplan = _apply_toml_sections(cfg, raw)
        _apply_content_file(cfg, plugin_dir, coplan)
    except Exception as exc:
        logger.warning(
            "Coplan config.toml 解析失败（%s），已回退默认值；"
            "请检查重复键或 TOML 语法: %s",
            path,
            exc,
        )
        return _defaults()
    return cfg


# ── 品牌与 Key 规范（原 brand.py）──

BRAND_NAME = "entropy"
BRAND_TITLE = "Entropy"
KEY_PREFIX = "sk-ent-"

# Anthropic sk-ant-api03-* 总长约 108 字符；sk-ent- 前缀更短，body 用 base64url 对齐总长
_KEY_BODY_BYTES = 76
_KEY_SAMPLE_BODY = secrets.token_urlsafe(_KEY_BODY_BYTES)
KEY_BODY_LENGTH = len(_KEY_SAMPLE_BODY)
KEY_TOTAL_LENGTH = len(KEY_PREFIX) + KEY_BODY_LENGTH


def generate_api_key() -> str:
    """生成 sk-ent-* API 密钥（格式与总长参考 Anthropic API Key）。"""
    return KEY_PREFIX + secrets.token_urlsafe(_KEY_BODY_BYTES)


# ── 默认套餐与模型种子数据（原 templates.py）──

DEFAULT_PLANS: List[Dict[str, Any]] = [
    {
        "id": "free",
        "name": "Free",
        "description": "体验入门，适合个人轻度使用",
        "price": 0,
        "requests_per_5h": 120,
        "requests_per_month": 6000,
        "features": ["基础模型访问", "社区支持"],
        "strategy_id": "default",
        "entry_alias": "fast",
    },
    {
        "id": "pro",
        "name": "Pro",
        "description": "推荐方案，适合日常开发与团队协作",
        "price": 29,
        "requests_per_5h": 240,
        "requests_per_month": 12000,
        "features": ["全量 Qwen 模型", "优先路由", "更高配额"],
        "strategy_id": "default",
        "entry_alias": "auto",
    },
    {
        "id": "ultra",
        "name": "Ultra",
        "description": "高强度使用，更大配额与推理模型",
        "price": 99,
        "requests_per_5h": 600,
        "requests_per_month": 30000,
        "features": ["推理模型优先", "最高配额", "专属支持"],
        "strategy_id": "default",
        "entry_alias": "reasoning",
    },
]

DEFAULT_MODELS: List[Dict[str, Any]] = [
    {
        "model_id": "qwen-plus",
        "display_name": "Qwen Plus",
        "description": "通用对话模型",
        "sort_order": 10,
    },
    {
        "model_id": "qwen-max",
        "display_name": "Qwen Max",
        "description": "高质量推理",
        "sort_order": 20,
    },
    {
        "model_id": "qwen-coder",
        "display_name": "Qwen Coder",
        "description": "代码生成",
        "sort_order": 30,
    },
]

# 兼容旧字段名；新代码请使用 CatalogStore 中的套餐数据
MARKET_TEMPLATES: List[Dict[str, Any]] = DEFAULT_PLANS
