/**
 * Parse the JSON response body of an api() call and enforce res.ok.
 * Split out of the CoplanUtils IIFE to keep that function under the line cap.
 */
function _coplanApiHandleResponse(res, locale) {
  var I18N = window.CoplanI18n;
  return res.json().then(function (data) {
    if (!res.ok) throw new Error(data.error || I18N.t('error.request', null, locale));
    return data;
  });
}

/**
 * Parse the models textarea/input value into a trimmed, deduped list.
 * Split out of the CoplanUtils IIFE to keep that function under the line cap.
 */
function _coplanParseModelsText(text) {
  return String(text || '').split(/[\n,]/).map(function (s) { return s.trim(); }).filter(Boolean);
}

/**
 * Copy text to the clipboard with an execCommand fallback, then toast.
 * Split out of the CoplanUtils IIFE to keep that function under the line cap.
 */
function _coplanCopyText(text, locale) {
  var I18N = window.CoplanI18n;
  var UI = window.CoplanUi;
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

/**
 * Base fetch helpers (headers/api) for CoplanUtils. Split out of the
 * CoplanUtils IIFE to keep it under the line cap.
 */
function _coplanHeaders(token) {
  return { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' };
}

function _coplanApi(apiBase, url, opts, token, locale) {
  opts = opts || {};
  return fetch(apiBase + url, Object.assign({}, opts, {
    headers: Object.assign({}, _coplanHeaders(token), opts.headers || {}),
  })).then(function (res) {
    return _coplanApiHandleResponse(res, locale);
  });
}

function _coplanParseFeatures(f) {
  try {
    return JSON.parse(f);
  } catch (e) {
    return f ? String(f).split('\n').filter(Boolean) : [];
  }
}

/**
 * Numeric/formatting helpers for CoplanUtils. Split out of the CoplanUtils
 * IIFE to keep it under the line cap.
 */
function _coplanFormatNumber(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return String(n);
}

function _coplanProgressClass(pct) {
  if (pct >= 90) return 'progress-red';
  if (pct >= 70) return 'progress-yellow';
  return 'progress-green';
}

function _coplanMaskKey(key) {
  if (!key || key.length < 12) return '***';
  return key.slice(0, 7) + '***' + key.slice(-4);
}

/**
 * Coplan shared utilities for portal apps (app + admin).
 * Exposes window.CoplanUtils with API helpers and formatters.
 */
(function () {
  'use strict';

  var API_BASE = window.location.origin;

  window.CoplanUtils = {
    apiBase: API_BASE,
    headers: _coplanHeaders,
    api: function (url, opts, token, locale) {
      return _coplanApi(API_BASE, url, opts, token, locale);
    },
    parseFeatures: _coplanParseFeatures,
    parseModelsText: _coplanParseModelsText,
    formatNumber: _coplanFormatNumber,
    progressClass: _coplanProgressClass,
    maskKey: _coplanMaskKey,
    copyText: _coplanCopyText,
  };
})();
