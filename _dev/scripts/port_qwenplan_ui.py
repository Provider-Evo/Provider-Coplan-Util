#!/usr/bin/env python3
"""从 qwenplan 模板生成 Coplan 静态 UI（Entropy 品牌）。"""
from __future__ import annotations

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "frontend_media"
QWEN = Path(r"X:\Project\Local\qwenplan\public")


def brand_replace(text: str) -> str:
    text = text.replace("AiJianCodingPlan", "Entropy CodingPlan")
    text = text.replace("AiJian", "Entropy")
    text = text.replace("爱简代码计划", "Entropy 代码计划")
    text = text.replace("ajcp_user_token", "ent_coplan_token")
    text = text.replace("ajcp_admin_token", "ent_coplan_admin_token")
    return text


def extract_body(html: str) -> str:
    body_start = html.index("<body>")
    body_end = html.rindex("</body>") + len("</body>")
    body = html[body_start:body_end]
    return re.sub(r"<script>.*</script>", "", body, flags=re.DOTALL)


def extract_script(html: str) -> str:
    match = re.search(r"<script>(.*)</script>", html, re.DOTALL)
    return match.group(1).strip() if match else ""


def patch_app_js(js: str) -> str:
    old = (
        "async function loadPublic() { try { const [p, c] = await Promise.all"
        "[fetch(API_BASE + '/api/plans').then(r => r.json()), "
        "fetch(API_BASE + '/api/admin-contact').then(r => r.json())]); "
        "publicPlans.value = p.plans || []; adminContact.value = c.contact || ''; } catch {} }"
    )
    new = """async function loadPublic() {
      try {
        const [marketRes, statusRes] = await Promise.all([
          fetch(API_BASE + '/v1/coplan/market/templates').then(function (r) { return r.json(); }),
          fetch(API_BASE + '/v1/coplan/status').then(function (r) { return r.json(); }),
        ]);
        const prices = [0, 29, 99];
        publicPlans.value = (marketRes.templates || []).map(function (t, i) {
          return {
            id: t.id,
            name: t.name,
            price: prices[i % prices.length],
            description: t.description,
            requests_per_5h: 120,
            requests_per_month: 6000,
            features: JSON.stringify(t.models || []),
          };
        });
        adminContact.value = (statusRes && statusRes.brand_title) ? statusRes.brand_title : 'Entropy';
        if (statusRes && statusRes.hero_tagline) {
          heroTagline.value = statusRes.hero_tagline;
        }
      } catch (e) { /* 首页静态展示不阻断 */ }
    }"""
    js = js.replace(old, new) if old in js else js
    if "const heroTagline = ref(" not in js:
        js = js.replace(
            "const publicPlans = ref([]); const adminContact = ref('');",
            "const publicPlans = ref([]); const adminContact = ref('');\n"
            "    const heroTagline = ref('高品质 AI API 代理服务，稳定、快速、可信赖。聚合多平台多模型，按策略组智能调度。');",
            1,
        )
    if "heroTagline," not in js:
        js = js.replace(
            "publicPlans, adminContact, activePlan",
            "publicPlans, adminContact, heroTagline, activePlan",
            1,
        )
    return js


def patch_admin_js(js: str) -> str:
    js = js.replace(
        "const users = ref([]); const plans = ref([]); const models = ref([]);",
        "const users = ref([]); const plans = ref([]); const models = ref([]);\n"
        "    const groupCount = ref(0); const marketCount = ref(0);",
        1,
    )
    old_load = (
        "async function loadAll() { if (!token.value) return; try { const [u, p, m, s] = await Promise.all"
        "([api('/api/admin/users'), api('/api/admin/plans'), api('/api/admin/models'), "
        "api('/api/admin/settings')]); users.value = u.users || []; plans.value = p.plans || []; "
        "models.value = m.models || []; Object.assign(settings, s.settings || {}); "
        "settingsForm.admin_contact = settings.admin_contact || ''; } catch (e) { console.error(e); } }"
    )
    new_load = """async function loadAll() {
      if (!token.value) return;
      try {
        const [statusRes, groupsRes, marketRes] = await Promise.all([
          fetch(API_BASE + '/v1/coplan/status').then(function (r) { return r.json(); }),
          fetch(API_BASE + '/v1/coplan/strategy-groups').then(function (r) { return r.json(); }),
          fetch(API_BASE + '/v1/coplan/market/templates').then(function (r) { return r.json(); }),
        ]);
        users.value = [];
        groupCount.value = (groupsRes.groups || []).length;
        marketCount.value = (marketRes.templates || []).length;
        plans.value = (marketRes.templates || []).map(function (t, i) {
          return {
            id: t.id,
            name: t.name,
            price: [0, 29, 99][i % 3],
            description: t.description,
            requests_per_5h: 120,
            requests_per_month: 6000,
            is_active: true,
            features: JSON.stringify(t.models || []),
            selected_models: JSON.stringify(t.models || []),
          };
        });
        models.value = (marketRes.templates || []).flatMap(function (t) {
          return (t.models || []).map(function (m, idx) {
            return {
              id: idx + 1,
              model_id: m,
              display_name: m,
              description: t.name,
              sort_order: idx,
              is_active: true,
            };
          });
        });
        settings.admin_contact = (statusRes && statusRes.brand_title) ? statusRes.brand_title : 'Entropy';
        settingsForm.admin_contact = settings.admin_contact;
      } catch (e) { console.error(e); }
    }"""
    if old_load in js:
        js = js.replace(old_load, new_load)
    js = js.replace(
        "return { token, loading, page, sidebarCollapsed, loginError, loginForm, users, plans, models, settings,",
        "return { token, loading, page, sidebarCollapsed, loginError, loginForm, users, plans, models, groupCount, marketCount, settings,",
        1,
    )
    return js


def patch_app_js(js: str) -> str:
    old = (
        "async function loadPublic() { try { const [p, c] = await Promise.all"
        "[fetch(API_BASE + '/api/plans').then(r => r.json()), "
        "fetch(API_BASE + '/api/admin-contact').then(r => r.json())]); "
        "publicPlans.value = p.plans || []; adminContact.value = c.contact || ''; } catch {} }"
    )
    new = """async function loadPublic() {
      try {
        const [marketRes, statusRes] = await Promise.all([
          fetch(API_BASE + '/v1/coplan/market/templates').then(function (r) { return r.json(); }),
          fetch(API_BASE + '/v1/coplan/status').then(function (r) { return r.json(); }),
        ]);
        const prices = [0, 29, 99];
        publicPlans.value = (marketRes.templates || []).map(function (t, i) {
          return {
            id: t.id,
            name: t.name,
            price: prices[i % prices.length],
            description: t.description,
            requests_per_5h: 120,
            requests_per_month: 6000,
            features: JSON.stringify(t.models || []),
          };
        });
        adminContact.value = (statusRes && statusRes.brand_title) ? statusRes.brand_title : 'Entropy';
        if (statusRes && statusRes.hero_tagline) {
          heroTagline.value = statusRes.hero_tagline;
        }
      } catch (e) { /* 首页静态展示不阻断 */ }
    }"""
    js = js.replace(old, new) if old in js else js
    if "const heroTagline = ref(" not in js:
        js = js.replace(
            "const publicPlans = ref([]); const adminContact = ref('');",
            "const publicPlans = ref([]); const adminContact = ref('');\n"
            "    const heroTagline = ref('高品质 AI API 代理服务，稳定、快速、可信赖。聚合多平台多模型，按策略组智能调度。');",
            1,
        )
    if "heroTagline," not in js:
        js = js.replace(
            "publicPlans, adminContact, activePlan",
            "publicPlans, adminContact, heroTagline, activePlan",
            1,
        )
    return js


def patch_admin_js(js: str) -> str:
    js = js.replace(
        "const users = ref([]); const plans = ref([]); const models = ref([]);",
        "const users = ref([]); const plans = ref([]); const models = ref([]);\n"
        "    const groupCount = ref(0); const marketCount = ref(0);",
        1,
    )
    old_load = (
        "async function loadAll() { if (!token.value) return; try { const [u, p, m, s] = await Promise.all"
        "([api('/api/admin/users'), api('/api/admin/plans'), api('/api/admin/models'), "
        "api('/api/admin/settings')]); users.value = u.users || []; plans.value = p.plans || []; "
        "models.value = m.models || []; Object.assign(settings, s.settings || {}); "
        "settingsForm.admin_contact = settings.admin_contact || ''; } catch (e) { console.error(e); } }"
    )
    new_load = """async function loadAll() {
      if (!token.value) return;
      try {
        const [statusRes, groupsRes, marketRes] = await Promise.all([
          fetch(API_BASE + '/v1/coplan/status').then(function (r) { return r.json(); }),
          fetch(API_BASE + '/v1/coplan/strategy-groups').then(function (r) { return r.json(); }),
          fetch(API_BASE + '/v1/coplan/market/templates').then(function (r) { return r.json(); }),
        ]);
        users.value = [];
        groupCount.value = (groupsRes.groups || []).length;
        marketCount.value = (marketRes.templates || []).length;
        plans.value = (marketRes.templates || []).map(function (t, i) {
          return {
            id: t.id,
            name: t.name,
            price: [0, 29, 99][i % 3],
            description: t.description,
            requests_per_5h: 120,
            requests_per_month: 6000,
            is_active: true,
            features: JSON.stringify(t.models || []),
            selected_models: JSON.stringify(t.models || []),
          };
        });
        models.value = (marketRes.templates || []).flatMap(function (t) {
          return (t.models || []).map(function (m, idx) {
            return {
              id: idx + 1,
              model_id: m,
              display_name: m,
              description: t.name,
              sort_order: idx,
              is_active: true,
            };
          });
        });
        settings.admin_contact = (statusRes && statusRes.brand_title) ? statusRes.brand_title : 'Entropy';
        settingsForm.admin_contact = settings.admin_contact;
      } catch (e) { console.error(e); }
    }"""
    if old_load in js:
        js = js.replace(old_load, new_load)
    js = js.replace(
        "return { token, loading, page, sidebarCollapsed, loginError, loginForm, users, plans, models, settings,",
        "return { token, loading, page, sidebarCollapsed, loginError, loginForm, users, plans, models, groupCount, marketCount, settings,",
        1,
    )
    return js


def main() -> None:
    app = QWEN.joinpath("app.html").read_text(encoding="utf-8")
    admin = QWEN.joinpath("admin.html").read_text(encoding="utf-8")

    index_head = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Entropy CodingPlan</title>
  <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/plugins/provider-coplan-util/styles/coplan.css">
</head>
"""

    admin_head = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Entropy CodingPlan - 管理后台</title>
  <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/plugins/provider-coplan-util/styles/coplan.css">
</head>
"""

    index_body = brand_replace(extract_body(app))
    index_body = index_body.replace(
        "<p class=\"animate-in delay-1\">高品质 AI API 代理服务，稳定、快速、可信赖。支持 Qwen 全系列模型。</p>",
        '<p class="animate-in delay-1">{{ heroTagline }}</p>',
    )
    index_body = index_body.replace(
        "<p class=\"animate-in delay-1\">高品质 AI API 代理服务，稳定、快速、可信赖。聚合多平台多模型，按策略组智能调度。</p>",
        '<p class="animate-in delay-1">{{ heroTagline }}</p>',
    )
    index_body = index_body.replace(
        "<p class=\"animate-in delay-1\">高品质 AI API 代理服务，稳定、快速、可信赖。聚合多平台多模型，按策略组智能调度。</p>",
        '<p class="animate-in delay-1">{{ heroTagline }}</p>',
    )
    STATIC.joinpath("index.html").write_text(
        index_head
        + index_body
        + '\n<script src="/static/plugins/provider-coplan-util/scripts/coplan-app.js"></script>\n</html>\n',
        encoding="utf-8",
    )
    STATIC.joinpath("admin.html").write_text(
        admin_head
        + brand_replace(extract_body(admin))
        + '\n<script src="/static/plugins/provider-coplan-util/scripts/coplan-admin.js"></script>\n</html>\n',
        encoding="utf-8",
    )
    STATIC.joinpath("coplan-app.js").write_text(
        patch_app_js(brand_replace(extract_script(app))) + "\n",
        encoding="utf-8",
    )
    STATIC.joinpath("coplan-admin.js").write_text(
        patch_admin_js(brand_replace(extract_script(admin))) + "\n",
        encoding="utf-8",
    )
    print("OK:", STATIC)


if __name__ == "__main__":
    main()
