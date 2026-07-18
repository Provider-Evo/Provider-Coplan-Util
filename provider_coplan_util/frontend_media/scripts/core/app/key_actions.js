var UI = window.CoplanUi;
var parseModelsText = window.CoplanAppUtils.parseModelsText;

function createKeyModalActions(d) {
  function showGenerateKey() {
    d.keyLabel.value = '';
    d.keyStrategyGroupId.value = '';
    d.keyAllowedModelsText.value = '';
    d.showKeyModal.value = true;
  }

  function openKeyConfig(k) {
    d.keyConfigTarget.value = k;
    d.keyConfigForm.strategy_group_id = k.strategy_group_id || '';
    d.keyConfigForm.allowed_models_text = (k.allowed_models || []).join('\n');
    d.showKeyConfigModal.value = true;
  }

  return { showGenerateKey, openKeyConfig };
}

function createKeyActions(d) {
  async function saveKeyConfig() {
    if (!d.keyConfigTarget.value) return;
    d.loading.value = true;
    try {
      await d.api('/api/user/api-keys/' + encodeURIComponent(d.keyConfigTarget.value.id), {
        method: 'PUT',
        body: JSON.stringify({
          strategy_group_id: d.keyConfigForm.strategy_group_id,
          allowed_models: parseModelsText(d.keyConfigForm.allowed_models_text),
        }),
      });
      d.showKeyConfigModal.value = false;
      await d.loadDashboard();
      UI.toast(d.t('admin.saved'), 'success');
    } finally {
      d.loading.value = false;
    }
  }

  async function doGenerateKey() {
    d.loading.value = true;
    try {
      var data = await d.api('/api/user/api-keys', {
        method: 'POST',
        body: JSON.stringify({
          label: d.keyLabel.value,
          strategy_group_id: d.keyStrategyGroupId.value,
          allowed_models: parseModelsText(d.keyAllowedModelsText.value),
        }),
      });
      d.newKey.value = data.key;
      d.showKeyModal.value = false;
      await d.loadDashboard();
    } finally {
      d.loading.value = false;
    }
  }

  return { saveKeyConfig, doGenerateKey };
}

function createKeyMiscActions(d) {
  async function revokeMyKey(k) {
    var ok = await UI.confirm(d.t('dash.revokeConfirm'), {
      title: d.t('dialog.confirmTitle'),
      confirmText: d.t('dash.revoke'),
      cancelText: d.t('dialog.cancel'),
      danger: true,
    });
    if (!ok) return;
    await d.api('/api/user/api-keys/' + k.id, { method: 'DELETE' });
    d.newKey.value = '';
    await d.loadDashboard();
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch (e) {
      var ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    UI.toast(d.t('dash.copied'), 'success');
  }

  return { revokeMyKey, copyText };
}

window.CoplanAppKeyActions = {
  createKeyModalActions: createKeyModalActions,
  createKeyActions: createKeyActions,
  createKeyMiscActions: createKeyMiscActions,
};
