function buildRouteModels(groups) {
  var rows = [];
  (groups || []).forEach(function (g) {
    var spec = g.spec || {};
    var aliases = spec.aliases || {};
    Object.keys(aliases).forEach(function (alias) {
      var block = aliases[alias] || {};
      var strategy = block.strategy || 'single';
      (block.routes || []).forEach(function (r) {
        rows.push({
          id: g.id + ':' + alias + ':' + (r.model || ''),
          alias: alias,
          strategy: strategy,
          platform: r.platform || '-',
          model: r.model || '-',
          group_name: g.name || g.id,
        });
      });
    });
    var def = spec.default;
    if (def && Array.isArray(def.routes)) {
      (def.routes || []).forEach(function (r) {
        rows.push({
          id: g.id + ':default:' + (r.model || ''),
          alias: '*',
          strategy: def.strategy || 'single',
          platform: r.platform || '-',
          model: r.model || '-',
          group_name: g.name || g.id,
        });
      });
    }
  });
  return rows;
}

function parseFeatures(f) {
  try {
    return JSON.parse(f);
  } catch (e) {
    return f ? String(f).split('\n').filter(Boolean) : [];
  }
}

function getPlanModels(p) {
  try {
    return JSON.parse(p.selected_models || '[]') || [];
  } catch (e) {
    return [];
  }
}

function createApiClient(token, locale) {
  function headers() {
    return { Authorization: 'Bearer ' + token.value, 'Content-Type': 'application/json' };
  }
  async function api(url, opts) {
    opts = opts || {};
    var res = await fetch(window.location.origin + url, Object.assign({}, opts, {
      headers: Object.assign({}, headers(), opts.headers || {}),
    }));
    var data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || window.CoplanI18n.t('error.request', null, locale.value));
    }
    return data;
  }
  return { api: api, headers: headers };
}

window.CoplanAdminUtils = {
  buildRouteModels: buildRouteModels,
  parseFeatures: parseFeatures,
  getPlanModels: getPlanModels,
  createApiClient: createApiClient,
};
