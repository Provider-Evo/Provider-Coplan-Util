/**
 * Coplan 命令式 UI：alert / confirm / prompt / toast
 * 不依赖 Vue，供脚本直接调用；prompt 通过 options.placeholder 传入占位提示。
 */
var COPLAN_UI_TOAST_DURATION = 3200;
var _coplanUiToastRoot = null;

function coplanUiT(key, vars) {
  if (window.CoplanI18n && typeof window.CoplanI18n.t === 'function') {
    return window.CoplanI18n.t(key, vars);
  }
  return key;
}

function coplanUiEscapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function coplanUiEscapeAttr(str) {
  return coplanUiEscapeHtml(str);
}

function coplanUiEnsureToastRoot() {
  if (_coplanUiToastRoot && document.body.contains(_coplanUiToastRoot)) return _coplanUiToastRoot;
  _coplanUiToastRoot = document.createElement('div');
  _coplanUiToastRoot.className = 'coplan-ui-toast-root';
  _coplanUiToastRoot.setAttribute('aria-live', 'polite');
  document.body.appendChild(_coplanUiToastRoot);
  return _coplanUiToastRoot;
}

function coplanUiCloseOverlay(overlay, resolve, value) {
  overlay.classList.remove('is-visible');
  setTimeout(function () {
    if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
    resolve(value);
  }, 180);
}

function coplanUiBindOverlayKeys(overlay, onConfirm, onCancel) {
  overlay.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      onCancel();
    }
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
      e.preventDefault();
      onConfirm();
    }
  });
}

function coplanUiBuildDialogHtml(options) {
  var dialogClass = 'coplan-ui-dialog' + (options.wide ? ' coplan-ui-dialog--wide' : '');
  var html = '<div class="' + dialogClass + '" role="dialog" aria-modal="true">';
  html += '<h3 class="coplan-ui-dialog__title">' + coplanUiEscapeHtml(options.title) + '</h3>';
  if (options.message) {
    html += '<div class="coplan-ui-dialog__message">' + coplanUiEscapeHtml(options.message) + '</div>';
  }
  if (options.mode === 'prompt') {
    html += '<input type="text" class="coplan-input coplan-ui-dialog__input" value="' +
      coplanUiEscapeAttr(options.defaultValue) + '" placeholder="' + coplanUiEscapeAttr(options.placeholder) + '">';
  }
  html += '<div class="coplan-ui-dialog__footer">';
  if (options.mode === 'confirm' || options.mode === 'prompt') {
    html += '<button type="button" class="btn btn-sm btn-outline coplan-ui-dialog__cancel">' +
      coplanUiEscapeHtml(options.cancelText) + '</button>';
  }
  var okClass = 'btn btn-sm ' + (options.danger ? 'btn-danger' : 'btn-primary') + ' coplan-ui-dialog__ok';
  html += '<button type="button" class="' + okClass + '">' + coplanUiEscapeHtml(options.confirmText) + '</button>';
  html += '</div></div>';
  return html;
}

function coplanUiFocusDialog(overlay) {
  var input = overlay.querySelector('.coplan-ui-dialog__input');
  if (input) {
    input.focus();
    input.select();
  } else {
    var okBtn = overlay.querySelector('.coplan-ui-dialog__ok');
    if (okBtn) okBtn.focus();
  }
  return input;
}

function coplanUiBindDialogEvents(overlay, input, mode, resolve) {
  function finish(value) {
    coplanUiCloseOverlay(overlay, resolve, value);
  }

  function onConfirm() {
    if (mode === 'prompt') {
      var value = input ? input.value.trim() : '';
      finish(value || null);
      return;
    }
    finish(mode === 'confirm' ? true : undefined);
  }

  function onCancel() {
    finish(mode === 'confirm' ? false : null);
  }

  overlay.querySelector('.coplan-ui-dialog__ok').addEventListener('click', onConfirm);
  var cancelBtn = overlay.querySelector('.coplan-ui-dialog__cancel');
  if (cancelBtn) cancelBtn.addEventListener('click', onCancel);
  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) onCancel();
  });
  coplanUiBindOverlayKeys(overlay, onConfirm, onCancel);
  if (input) {
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        onConfirm();
      }
    });
  }
}

function coplanUiOpenDialog(options) {
  options = options || {};
  var mode = options.mode || 'alert';
  var normalized = {
    mode: mode,
    title: options.title || coplanUiT('dialog.titleDefault'),
    message: options.message || '',
    confirmText: options.confirmText || coplanUiT('dialog.ok'),
    cancelText: options.cancelText || coplanUiT('dialog.cancel'),
    placeholder: options.placeholder || '',
    defaultValue: options.defaultValue || '',
    danger: !!options.danger,
    wide: !!options.wide,
  };

  return new Promise(function (resolve) {
    var overlay = document.createElement('div');
    overlay.className = 'coplan-ui-overlay';
    overlay.setAttribute('role', 'presentation');
    overlay.innerHTML = coplanUiBuildDialogHtml(normalized);
    document.body.appendChild(overlay);
    requestAnimationFrame(function () { overlay.classList.add('is-visible'); });

    var input = coplanUiFocusDialog(overlay);
    coplanUiBindDialogEvents(overlay, input, mode, resolve);
  });
}

function coplanUiToast(message, type) {
  var root = coplanUiEnsureToastRoot();
  var node = document.createElement('div');
  node.className = 'coplan-ui-toast coplan-ui-toast--' + (type || 'info');
  node.textContent = String(message);
  root.appendChild(node);
  requestAnimationFrame(function () { node.classList.add('is-visible'); });
  setTimeout(function () {
    node.classList.remove('is-visible');
    setTimeout(function () { node.remove(); }, 200);
  }, COPLAN_UI_TOAST_DURATION);
}

(function () {
  'use strict';

  window.CoplanUi = {
    alert: function (message, options) {
      options = Object.assign({ mode: 'alert', message: message }, options || {});
      return coplanUiOpenDialog(options);
    },
    confirm: function (message, options) {
      options = Object.assign({ mode: 'confirm', message: message }, options || {});
      return coplanUiOpenDialog(options);
    },
    prompt: function (message, options) {
      options = Object.assign({ mode: 'prompt', message: message }, options || {});
      return coplanUiOpenDialog(options);
    },
    toast: coplanUiToast,
    t: coplanUiT,
  };
})();
