var UI = window.CoplanUi;

function createStrategyListActions(d) {
  async function loadStrategies() {
    if (!d.token.value) return;
    try {
      var res = await d.api('/api/user/strategy-groups');
      d.myGroups.value = res.groups || [];
      if (res.strategy_prefix) d.strategyPrefix.value = res.strategy_prefix;
    } catch (e) {
      console.error(e);
    }
  }

  async function createStrategyGroup() {
    var name = await UI.prompt(d.t('dash.strategyName'), { placeholder: 'my-routing', title: d.t('dash.strategyCreate') });
    if (!name) return;
    d.loading.value = true;
    try {
      await d.api('/api/user/strategy-groups', { method: 'POST', body: JSON.stringify({ name: name }) });
      await loadStrategies();
      UI.toast(d.t('admin.saved'), 'success');
    } catch (e) {
      await UI.alert(String(e.message || e), { title: d.t('dialog.errorTitle') });
    } finally {
      d.loading.value = false;
    }
  }

  return { loadStrategies, createStrategyGroup };
}

function createStrategyCodeActions(d) {
  async function openStrategyEditor(g) {
    d.strategyTarget.value = g;
    d.loading.value = true;
    try {
      var res = await d.api('/api/user/strategy-groups/' + encodeURIComponent(g.id) + '/code');
      d.strategyCode.value = res.source_code || '';
      d.compiledSpecText.value = JSON.stringify(res.compiled_spec || {}, null, 2);
      d.showStrategyModal.value = true;
    } finally {
      d.loading.value = false;
    }
  }

  async function validateStrategyCode() {
    d.loading.value = true;
    try {
      var res = await d.api('/api/user/strategy-groups/compile', {
        method: 'POST',
        body: JSON.stringify({ source_code: d.strategyCode.value }),
      });
      d.compiledSpecText.value = JSON.stringify(res.spec || {}, null, 2);
      UI.toast(d.t('dash.strategyValidated'), 'success');
    } catch (e) {
      await UI.alert(String(e.message || e), { title: d.t('dialog.errorTitle') });
    } finally {
      d.loading.value = false;
    }
  }

  async function saveStrategyCode() {
    if (!d.strategyTarget.value) return;
    d.loading.value = true;
    try {
      await d.api('/api/user/strategy-groups/' + encodeURIComponent(d.strategyTarget.value.id) + '/code', {
        method: 'PUT',
        body: JSON.stringify({ source_code: d.strategyCode.value }),
      });
      d.showStrategyModal.value = false;
      await d.loadStrategies();
      UI.toast(d.t('dash.strategySaved'), 'success');
    } catch (e) {
      await UI.alert(String(e.message || e), { title: d.t('dialog.errorTitle') });
    } finally {
      d.loading.value = false;
    }
  }

  return { openStrategyEditor, validateStrategyCode, saveStrategyCode };
}

function createStrategyKeyBindActions(d) {
  function openStrategyKeyBind(g) {
    d.strategyKeyTarget.value = g;
    d.strategyAllowedKeyIds.value = (g.allowed_key_ids || []).slice();
    d.showStrategyKeysModal.value = true;
  }

  function toggleStrategyKey(id) {
    var index = d.strategyAllowedKeyIds.value.indexOf(id);
    if (index >= 0) d.strategyAllowedKeyIds.value.splice(index, 1);
    else d.strategyAllowedKeyIds.value.push(id);
  }

  async function saveStrategyKeyBind() {
    if (!d.strategyKeyTarget.value) return;
    d.loading.value = true;
    try {
      await d.api('/api/user/strategy-groups/' + encodeURIComponent(d.strategyKeyTarget.value.id) + '/keys', {
        method: 'PUT',
        body: JSON.stringify({ key_ids: d.strategyAllowedKeyIds.value }),
      });
      d.showStrategyKeysModal.value = false;
      await d.loadStrategies();
      UI.toast(d.t('admin.saved'), 'success');
    } finally {
      d.loading.value = false;
    }
  }

  return { openStrategyKeyBind, toggleStrategyKey, saveStrategyKeyBind };
}

function createStrategyLifecycleActions(d) {
  async function publishStrategy(g) {
    d.loading.value = true;
    try {
      await d.api('/api/user/strategy-groups/' + encodeURIComponent(g.id) + '/publish', {
        method: 'POST',
        body: JSON.stringify({ title: g.name, description: g.description || '' }),
      });
      UI.toast(d.t('dash.strategyPublished'), 'success');
    } catch (e) {
      await UI.alert(String(e.message || e), { title: d.t('dialog.errorTitle') });
    } finally {
      d.loading.value = false;
    }
  }

  async function deleteStrategy(g) {
    var ok = await UI.confirm(d.t('dash.strategyDeleteConfirm', { name: g.name }), {
      title: d.t('dialog.confirmTitle'),
      confirmText: d.t('admin.delete'),
      cancelText: d.t('dialog.cancel'),
      danger: true,
    });
    if (!ok) return;
    d.loading.value = true;
    try {
      await d.api('/api/user/strategy-groups/' + encodeURIComponent(g.id), { method: 'DELETE' });
      await d.loadStrategies();
    } finally {
      d.loading.value = false;
    }
  }

  return { publishStrategy, deleteStrategy };
}

window.CoplanAppStrategyActions = {
  createStrategyListActions: createStrategyListActions,
  createStrategyCodeActions: createStrategyCodeActions,
  createStrategyKeyBindActions: createStrategyKeyBindActions,
  createStrategyLifecycleActions: createStrategyLifecycleActions,
};
