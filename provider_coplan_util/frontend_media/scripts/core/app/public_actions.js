var API_BASE = window.location.origin;
var UI = window.CoplanUi;

function mapPublicPlans(publicRes, marketRes) {
  return (publicRes.plans || marketRes.plans || []).map(function (tpl) {
    return {
      id: tpl.id,
      name: tpl.name,
      price: tpl.price != null ? tpl.price : 0,
      description: tpl.description,
      requests_per_5h: tpl.requests_per_5h || 120,
      requests_per_month: tpl.requests_per_month || 6000,
      features: typeof tpl.features === 'string' ? tpl.features : JSON.stringify(Array.isArray(tpl.features) ? tpl.features : []),
    };
  });
}

function applyPublicStatus(d, statusRes, publicRes) {
  if (statusRes && statusRes.hero_tagline) {
    d.heroTagline.value = statusRes.hero_tagline;
  }
  if (statusRes && statusRes.brand_title && !publicRes.admin_contact) {
    d.adminContact.value = statusRes.brand_title;
  }
  if (statusRes && statusRes.strategy_prefix) {
    d.strategyPrefix.value = statusRes.strategy_prefix;
  }
}

function createPublicActions(d) {
  function applyPublicPayload(payload) {
    if (!payload || typeof payload !== 'object') return;
    d.heroTagline.value = payload.hero_tagline || d.heroTagline.value;
    d.agentsTitle.value = payload.agents_title || d.agentsTitle.value;
    d.advantagesTitle.value = payload.advantages_title || d.advantagesTitle.value;
    d.pricingTitle.value = payload.pricing_title || d.pricingTitle.value;
    d.faqTitle.value = payload.faq_title || d.faqTitle.value;
    d.contactHint.value = payload.contact_hint || d.contactHint.value;
    d.adminContact.value = payload.admin_contact || d.adminContact.value;
    d.agents.value = Array.isArray(payload.agents) ? payload.agents : [];
    d.advantages.value = Array.isArray(payload.advantages) ? payload.advantages : [];
    d.platforms.value = Array.isArray(payload.platforms) ? payload.platforms : [];
    if (Array.isArray(payload.faqs) && payload.faqs.length) {
      d.faqs.splice(0, d.faqs.length);
      payload.faqs.forEach(function (item) {
        d.faqs.push({ q: item.q, a: item.a, open: false });
      });
    }
  }

  async function loadPublic() {
    try {
      var results = await Promise.all([
        fetch(API_BASE + '/v1/coplan/public').then(function (r) { return r.json(); }),
        fetch(API_BASE + '/v1/coplan/market/templates').then(function (r) { return r.json(); }),
        fetch(API_BASE + '/v1/coplan/status').then(function (r) { return r.json(); }),
      ]);
      var publicRes = results[0];
      var marketRes = results[1];
      var statusRes = results[2];
      applyPublicPayload(publicRes);
      applyPublicStatus(d, statusRes, publicRes);
      d.publicPlans.value = mapPublicPlans(publicRes, marketRes);
    } catch (e) {
      console.debug('loadPublic:', e);
    }
  }

  return { loadPublic, applyPublicPayload };
}

function createMarketActions(d) {
  async function loadMarket() {
    try {
      var res = await fetch(API_BASE + '/v1/coplan/strategy-market');
      var data = await res.json();
      d.marketEntries.value = data.entries || [];
    } catch (e) {
      console.error(e);
    }
  }

  function viewMarketEntry(entry) {
    d.marketEntryTarget.value = entry;
    d.showMarketEntryModal.value = true;
  }

  async function forkMarketEntry(entry) {
    if (!entry || !d.token.value) return;
    d.loading.value = true;
    try {
      await d.api('/api/user/strategy-groups/fork', {
        method: 'POST',
        body: JSON.stringify({ market_entry_id: entry.id }),
      });
      d.showMarketEntryModal.value = false;
      await d.loadStrategies();
      d.dashTab.value = 'strategies';
      UI.toast(d.t('dash.marketForkOk'), 'success');
    } catch (e) {
      await UI.alert(String(e.message || e), { title: d.t('dialog.errorTitle') });
    } finally {
      d.loading.value = false;
    }
  }

  return { loadMarket, viewMarketEntry, forkMarketEntry };
}

window.CoplanAppPublicActions = {
  mapPublicPlans: mapPublicPlans,
  applyPublicStatus: applyPublicStatus,
  createPublicActions: createPublicActions,
  createMarketActions: createMarketActions,
};
