function parseFeatures(f) {
  try {
    return JSON.parse(f);
  } catch (e) {
    return f ? String(f).split('\n').filter(Boolean) : [];
  }
}

function progressClass(pct) {
  if (pct >= 90) return 'progress-red';
  if (pct >= 70) return 'progress-yellow';
  return 'progress-green';
}

function formatNumber(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return String(n);
}

function parseModelsText(text) {
  return String(text || '').split(/[\n,]/).map(function (s) { return s.trim(); }).filter(Boolean);
}

function maskKey(key) {
  if (!key || key.length < 12) return '***';
  return key.slice(0, 7) + '***' + key.slice(-4);
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
    if (!res.ok) throw new Error(data.error || window.CoplanI18n.t('error.request', null, locale.value));
    return data;
  }
  return { api: api, headers: headers };
}

window.CoplanAppUtils = {
  parseFeatures: parseFeatures,
  progressClass: progressClass,
  formatNumber: formatNumber,
  parseModelsText: parseModelsText,
  maskKey: maskKey,
  createApiClient: createApiClient,
};
