/**
 * Coplan 命令式 UI：alert / confirm / prompt / toast
 * 不依赖 Vue，供脚本直接调用；prompt 通过 options.placeholder 传入占位提示。
 */
(function () {
  'use strict';

  var TOAST_DURATION = 3200;
  var _toastRoot = null;

  function t(key, vars) {
    if (window.CoplanI18n && typeof window.CoplanI18n.t === 'function') {
      return window.CoplanI18n.t(key, vars);
    }
    return key;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function escapeAttr(str) {
    return escapeHtml(str);
  }

  function ensureToastRoot() {
    if (_toastRoot && document.body.contains(_toastRoot)) return _toastRoot;
    _toastRoot = document.createElement('div');
    _toastRoot.className = 'coplan-ui-toast-root';
    _toastRoot.setAttribute('aria-live', 'polite');
    document.body.appendChild(_toastRoot);
    return _toastRoot;
  }

  function closeOverlay(overlay, resolve, value) {
    overlay.classList.remove('is-visible');
    setTimeout(function () {
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      resolve(value);
    }, 180);
  }

  function bindOverlayKeys(overlay, onConfirm, onCancel) {
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

  function openDialog(options) {
    options = options || {};
    var mode = options.mode || 'alert';
    var title = options.title || t('dialog.titleDefault');
    var message = options.message || '';
    var confirmText = options.confirmText || t('dialog.ok');
    var cancelText = options.cancelText || t('dialog.cancel');
    var placeholder = options.placeholder || '';
    var defaultValue = options.defaultValue || '';
    var danger = !!options.danger;
    var wide = !!options.wide;

    return new Promise(function (resolve) {
      var overlay = document.createElement('div');
      overlay.className = 'coplan-ui-overlay';
      overlay.setAttribute('role', 'presentation');

      var dialogClass = 'coplan-ui-dialog' + (wide ? ' coplan-ui-dialog--wide' : '');
      var html = '<div class="' + dialogClass + '" role="dialog" aria-modal="true">';
      html += '<h3 class="coplan-ui-dialog__title">' + escapeHtml(title) + '</h3>';
      if (message) {
        html += '<div class="coplan-ui-dialog__message">' + escapeHtml(message) + '</div>';
      }
      if (mode === 'prompt') {
        html += '<input type="text" class="coplan-input coplan-ui-dialog__input" value="' +
          escapeAttr(defaultValue) + '" placeholder="' + escapeAttr(placeholder) + '">';
      }
      html += '<div class="coplan-ui-dialog__footer">';
      if (mode === 'confirm' || mode === 'prompt') {
        html += '<button type="button" class="btn btn-sm btn-outline coplan-ui-dialog__cancel">' +
          escapeHtml(cancelText) + '</button>';
      }
      var okClass = 'btn btn-sm ' + (danger ? 'btn-danger' : 'btn-primary') + ' coplan-ui-dialog__ok';
      html += '<button type="button" class="' + okClass + '">' + escapeHtml(confirmText) + '</button>';
      html += '</div></div>';

      overlay.innerHTML = html;
      document.body.appendChild(overlay);
      requestAnimationFrame(function () { overlay.classList.add('is-visible'); });

      var input = overlay.querySelector('.coplan-ui-dialog__input');
      if (input) {
        input.focus();
        input.select();
      } else {
        var okBtn = overlay.querySelector('.coplan-ui-dialog__ok');
        if (okBtn) okBtn.focus();
      }

      function finish(value) {
        closeOverlay(overlay, resolve, value);
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
      bindOverlayKeys(overlay, onConfirm, onCancel);
      if (input) {
        input.addEventListener('keydown', function (e) {
          if (e.key === 'Enter') {
            e.preventDefault();
            onConfirm();
          }
        });
      }
    });
  }

  function toast(message, type) {
    var root = ensureToastRoot();
    var node = document.createElement('div');
    node.className = 'coplan-ui-toast coplan-ui-toast--' + (type || 'info');
    node.textContent = String(message);
    root.appendChild(node);
    requestAnimationFrame(function () { node.classList.add('is-visible'); });
    setTimeout(function () {
      node.classList.remove('is-visible');
      setTimeout(function () { node.remove(); }, 200);
    }, TOAST_DURATION);
  }

  window.CoplanUi = {
    alert: function (message, options) {
      options = Object.assign({ mode: 'alert', message: message }, options || {});
      return openDialog(options);
    },
    confirm: function (message, options) {
      options = Object.assign({ mode: 'confirm', message: message }, options || {});
      return openDialog(options);
    },
    prompt: function (message, options) {
      options = Object.assign({ mode: 'prompt', message: message }, options || {});
      return openDialog(options);
    },
    toast: toast,
    t: t,
  };
})();
