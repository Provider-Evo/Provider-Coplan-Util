/**
 * Read the WebUI-stored theme setting as a fallback for the Coplan theme
 * key. Split out of the theme IIFE to keep it under the line cap.
 */
function _coplanReadWebUiTheme() {
  var WEBUI_SETTINGS_KEY = 'provider.webui.settings';
  try {
    var settings = JSON.parse(localStorage.getItem(WEBUI_SETTINGS_KEY) || '{}');
    if (settings.theme) return settings.theme;
  } catch (e) { /* ignore */ }
  return null;
}

var _COPLAN_THEME_STORAGE_KEY = 'coplan_theme';

function _coplanReadStoredTheme() {
  var stored = localStorage.getItem(_COPLAN_THEME_STORAGE_KEY);
  if (stored) return stored;
  var webuiTheme = _coplanReadWebUiTheme();
  if (webuiTheme) return webuiTheme;
  return 'auto';
}

function _coplanEffectiveTheme(theme) {
  if (theme === 'auto') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return theme === 'dark' ? 'dark' : 'light';
}

function _coplanUpdateThemeIcons(theme) {
  var effective = _coplanEffectiveTheme(theme);
  var html = effective === 'dark' ? '&#9788;' : '&#9790;';
  document.querySelectorAll('.coplan-theme-icon').forEach(function (node) {
    node.innerHTML = html;
  });
}

function _coplanApplyTheme(theme) {
  var value = theme || _coplanReadStoredTheme();
  var effective = _coplanEffectiveTheme(value);
  document.documentElement.setAttribute('data-theme', effective);
  document.documentElement.style.colorScheme = effective;
  _coplanUpdateThemeIcons(value);
  window.dispatchEvent(new CustomEvent('coplan:theme-change', {
    detail: { theme: value, effective: effective },
  }));
}

function _coplanToggleTheme() {
  var stored = localStorage.getItem(_COPLAN_THEME_STORAGE_KEY);
  var current = stored || _coplanReadStoredTheme();
  var effective = _coplanEffectiveTheme(current);
  var next = effective === 'light' ? 'dark' : 'light';
  localStorage.setItem(_COPLAN_THEME_STORAGE_KEY, next);
  _coplanApplyTheme(next);
}

function _bindSystemThemeListener() {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
    var stored = localStorage.getItem(_COPLAN_THEME_STORAGE_KEY);
    var active = stored || _coplanReadWebUiTheme() || 'auto';
    if (active === 'auto') _coplanApplyTheme('auto');
  });
}

/**
 * Coplan theme toggle (light / dark / auto), aligned with WebUI settings.
 * Logic lives in the standalone _coplan* functions above; this IIFE only
 * wires DOM listeners and exposes the public window.CoplanTheme API.
 */
(function () {
  document.addEventListener('click', function (event) {
    var target = event.target;
    if (!target) return;
    var btn = target.closest && target.closest('.coplan-theme-btn');
    if (btn) _coplanToggleTheme();
  });

  document.addEventListener('DOMContentLoaded', function () {
    _coplanApplyTheme(_coplanReadStoredTheme());
  });

  _bindSystemThemeListener();

  window.CoplanTheme = { apply: _coplanApplyTheme, toggle: _coplanToggleTheme, read: _coplanReadStoredTheme };
})();
