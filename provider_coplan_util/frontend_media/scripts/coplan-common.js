/**
 * Coplan shared utilities for portal apps (app + admin).
 * Exposes window.CoplanUtils with API helpers and formatters.
 */
(function () {
  'use strict';

  var API_BASE = window.location.origin;
  var I18N = window.CoplanI18n;
  var UI = window.CoplanUi;

  function headers(token) {
    return { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' };
  }

  function api(url, opts, token, locale) {
    opts = opts || {};
    return fetch(API_BASE + url, Object.assign({}, opts, {
      headers: Object.assign({}, headers(token), opts.headers || {}),
    })).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) throw new Error(data.error || I18N.t('error.request', null, locale));
        return data;
      });
    });
  }

  function parseFeatures(f) {
    try {
      return JSON.parse(f);
    } catch (e) {
      return f ? String(f).split('\n').filter(Boolean) : [];
    }
  }

  function parseModelsText(text) {
    return String(text || '').split(/[\n,]/).map(function (s) { return s.trim(); }).filter(Boolean);
  }

  function formatNumber(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return String(n);
  }

  function progressClass(pct) {
    if (pct >= 90) return 'progress-red';
    if (pct >= 70) return 'progress-yellow';
    return 'progress-green';
  }

  function maskKey(key) {
    if (!key || key.length < 12) return '***';
    return key.slice(0, 7) + '***' + key.slice(-4);
  }

  function copyText(text, locale) {
    return navigator.clipboard.writeText(text).catch(function () {
      var ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }).then(function () {
      UI.toast(I18N.t('dash.copied', null, locale), 'success');
    });
  }

  window.CoplanUtils = {
    apiBase: API_BASE,
    headers: headers,
    api: api,
    parseFeatures: parseFeatures,
    parseModelsText: parseModelsText,
    formatNumber: formatNumber,
    progressClass: progressClass,
    maskKey: maskKey,
    copyText: copyText,
  };
})();
