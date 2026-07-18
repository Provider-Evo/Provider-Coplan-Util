var UI = window.CoplanUi;

function createGroupCreateAction(d) {
  async function createGroup() {
    var name = (d.newGroupName.value || '').trim();
    if (!name) return;
    d.loading.value = true;
    try {
      await d.api('/v1/coplan/strategy-groups', {
        method: 'POST',
        body: JSON.stringify({ name: name, description: d.newGroupDesc.value || '' }),
      });
      d.newGroupName.value = '';
      d.newGroupDesc.value = '';
      await d.loadAll();
    } finally {
      d.loading.value = false;
    }
  }

  return { createGroup };
}

function createGroupCrudActions(d) {
  async function deleteGroup(g) {
    if (g.source === 'code') return;
    var ok = await UI.confirm(d.t('admin.deleteGroupConfirm', { name: g.name }), {
      title: d.t('dialog.confirmTitle'),
      confirmText: d.t('admin.delete'),
      cancelText: d.t('dialog.cancel'),
      danger: true,
    });
    if (!ok) return;
    d.loading.value = true;
    try {
      await d.api('/v1/coplan/strategy-groups/' + encodeURIComponent(g.id), { method: 'DELETE' });
      await d.loadAll();
    } finally {
      d.loading.value = false;
    }
  }

  async function publishGroup(g) {
    var ok = await UI.confirm(d.t('admin.publishConfirm', { name: g.name }), {
      title: d.t('dialog.confirmTitle'),
      confirmText: d.t('admin.marketPublish'),
      cancelText: d.t('dialog.cancel'),
    });
    if (!ok) return;
    d.loading.value = true;
    try {
      await d.api('/v1/coplan/strategy-market', {
        method: 'POST',
        body: JSON.stringify({
          group_id: g.id,
          title: g.name,
          description: g.description || '',
        }),
      });
      UI.toast(d.t('admin.published'), 'success');
      await d.loadAll();
    } catch (e) {
      await UI.alert(String(e.message || e), { title: d.t('dialog.errorTitle') });
    } finally {
      d.loading.value = false;
    }
  }

  return { deleteGroup, publishGroup };
}

function createGroupCodeOpenAction(d) {
  async function openGroupCode(g) {
    d.codeTarget.value = g;
    d.codeReadonly.value = g.source === 'code';
    d.loading.value = true;
    try {
      var data = await d.api('/v1/coplan/strategy-groups/' + encodeURIComponent(g.id) + '/code');
      d.strategyCode.value = data.source_code || '';
      d.compiledSpecText.value = JSON.stringify(data.compiled_spec || {}, null, 2);
      d.showCodeModal.value = true;
    } catch (e) {
      await UI.alert(String(e.message || e), { title: d.t('dialog.errorTitle') });
    } finally {
      d.loading.value = false;
    }
  }

  return { openGroupCode };
}

function createGroupCodeActions(d) {
  var openAction = createGroupCodeOpenAction(d);
  var openGroupCode = openAction.openGroupCode;

  async function validateStrategyCode() {
    d.loading.value = true;
    try {
      var data = await d.api('/v1/coplan/strategy-groups/compile', {
        method: 'POST',
        body: JSON.stringify({ source_code: d.strategyCode.value }),
      });
      d.compiledSpecText.value = JSON.stringify(data.spec || {}, null, 2);
      UI.toast(d.t('admin.strategyValidated'), 'success');
    } catch (e) {
      await UI.alert(String(e.message || e), { title: d.t('dialog.errorTitle') });
    } finally {
      d.loading.value = false;
    }
  }

  async function saveStrategyCode() {
    if (!d.codeTarget.value || d.codeReadonly.value) return;
    d.loading.value = true;
    try {
      await d.api('/v1/coplan/strategy-groups/' + encodeURIComponent(d.codeTarget.value.id) + '/code', {
        method: 'PUT',
        body: JSON.stringify({ source_code: d.strategyCode.value }),
      });
      d.showCodeModal.value = false;
      UI.toast(d.t('admin.strategySaved'), 'success');
      await d.loadAll();
    } catch (e) {
      await UI.alert(String(e.message || e), { title: d.t('dialog.errorTitle') });
    } finally {
      d.loading.value = false;
    }
  }

  return { openGroupCode, validateStrategyCode, saveStrategyCode };
}

function _refreshGroupKeysTarget(d) {
  var refreshed = d.groups.value.find(function (g) { return g.id === d.keysTarget.value.id; });
  if (refreshed) {
    d.keysTarget.value = refreshed;
    d.userKeys.value = refreshed.keys || [];
  }
}

function _createGroupKeyDeleteAction(d) {
  async function deleteKey(k) {
    if (!d.keysTarget.value) return;
    var ok = await UI.confirm(d.t('admin.deleteKeyConfirm', { key: k.key || k.id }), {
      title: d.t('dialog.confirmTitle'),
      confirmText: d.t('admin.delete'),
      cancelText: d.t('dialog.cancel'),
      danger: true,
    });
    if (!ok) return;
    d.loading.value = true;
    try {
      await d.api('/v1/coplan/strategy-groups/' + encodeURIComponent(d.keysTarget.value.id) + '/keys/' + encodeURIComponent(k.id), {
        method: 'DELETE',
      });
      await d.loadAll();
      _refreshGroupKeysTarget(d);
    } finally {
      d.loading.value = false;
    }
  }

  return deleteKey;
}

function createGroupKeyActions(d) {
  function openGroupKeys(g) {
    d.keysTarget.value = g;
    d.newKey.value = '';
    d.showKeysModal.value = true;
    loadGroupKeys();
  }

  async function loadGroupKeys() {
    if (!d.keysTarget.value) return;
    d.userKeys.value = d.keysTarget.value.keys || [];
  }

  async function generateKey() {
    if (!d.keysTarget.value) return;
    d.loading.value = true;
    try {
      var data = await d.api('/v1/coplan/strategy-groups/' + encodeURIComponent(d.keysTarget.value.id) + '/keys', {
        method: 'POST',
        body: JSON.stringify({ label: 'admin' }),
      });
      d.newKey.value = data.key || (data.entry && data.entry.key) || '';
      await d.loadAll();
      _refreshGroupKeysTarget(d);
    } finally {
      d.loading.value = false;
    }
  }

  var deleteKey = _createGroupKeyDeleteAction(d);

  return { openGroupKeys, generateKey, deleteKey };
}

window.CoplanAdminGroupActions = {
  createGroupCreateAction: createGroupCreateAction,
  createGroupCrudActions: createGroupCrudActions,
  createGroupCodeActions: createGroupCodeActions,
  createGroupKeyActions: createGroupKeyActions,
};
