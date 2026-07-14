/**
 * Coplan theme toggle (light / dark / auto), aligned with WebUI settings.
 */
(function () {
  var STORAGE_KEY = 'coplan_theme';
  var WEBUI_SETTINGS_KEY = 'provider.webui.settings';

  function readWebUiTheme() {
    try {
      var settings = JSON.parse(localStorage.getItem(WEBUI_SETTINGS_KEY) || '{}');
      if (settings.theme) return settings.theme;
    } catch (e) { /* ignore */ }
    return null;
  }

  function readStoredTheme() {
    var stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
    var webuiTheme = readWebUiTheme();
    if (webuiTheme) return webuiTheme;
    return 'auto';
  }

  function effectiveTheme(theme) {
    if (theme === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return theme === 'dark' ? 'dark' : 'light';
  }

  function updateIcons(theme) {
    var effective = effectiveTheme(theme);
    var html = effective === 'dark' ? '&#9788;' : '&#9790;';
    document.querySelectorAll('.coplan-theme-icon').forEach(function (node) {
      node.innerHTML = html;
    });
  }

  function applyTheme(theme) {
    var value = theme || readStoredTheme();
    var effective = effectiveTheme(value);
    document.documentElement.setAttribute('data-theme', effective);
    document.documentElement.style.colorScheme = effective;
    updateIcons(value);
    window.dispatchEvent(new CustomEvent('coplan:theme-change', {
      detail: { theme: value, effective: effective },
    }));
  }

  function toggleTheme() {
    var stored = localStorage.getItem(STORAGE_KEY);
    var current = stored || readStoredTheme();
    var effective = effectiveTheme(current);
    var next = effective === 'light' ? 'dark' : 'light';
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  }

  document.addEventListener('click', function (event) {
    var target = event.target;
    if (!target) return;
    var btn = target.closest && target.closest('.coplan-theme-btn');
    if (btn) toggleTheme();
  });

  document.addEventListener('DOMContentLoaded', function () {
    applyTheme(readStoredTheme());
  });

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
    var stored = localStorage.getItem(STORAGE_KEY);
    var active = stored || readWebUiTheme() || 'auto';
    if (active === 'auto') applyTheme('auto');
  });

  window.CoplanTheme = { apply: applyTheme, toggle: toggleTheme, read: readStoredTheme };
})();
