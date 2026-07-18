var UI = window.CoplanUi;

async function _loadMarketSpecText(d, entry) {
  try {
    var data = await d.api('/v1/coplan/strategy-market/' + encodeURIComponent(entry.id));
    var text = (data.entry && data.entry.source_code) || '';
    if (!text) {
      text = JSON.stringify((data.entry && data.entry.spec) || entry.spec || {}, null, 2);
    }
    return text;
  } catch (e) {
    return JSON.stringify(entry.spec || {}, null, 2);
  }
}

async function _openMarketSpec(d, entry) {
  d.marketSpecTarget.value = entry;
  d.loading.value = true;
  try {
    d.marketSpecText.value = await _loadMarketSpecText(d, entry);
    d.showMarketSpecModal.value = true;
  } finally {
    d.loading.value = false;
  }
}

async function _forkMarketEntry(d, entry) {
  var ok = await UI.confirm(d.t('admin.forkConfirm', { name: entry.title }), {
    title: d.t('dialog.confirmTitle'),
    confirmText: d.t('admin.marketFork'),
    cancelText: d.t('dialog.cancel'),
  });
  if (!ok) return;
  d.loading.value = true;
  try {
    await d.api('/v1/coplan/strategy-market/' + encodeURIComponent(entry.id) + '/fork', {
      method: 'POST',
      body: JSON.stringify({ name: entry.title + '-fork' }),
    });
    UI.toast(d.t('admin.forked'), 'success');
    await d.loadAll();
  } catch (e) {
    await UI.alert(String(e.message || e), { title: d.t('dialog.errorTitle') });
  } finally {
    d.loading.value = false;
  }
}

async function _deleteMarketEntry(d, entry) {
  var ok = await UI.confirm(d.t('admin.deleteMarketConfirm', { name: entry.title }), {
    title: d.t('dialog.confirmTitle'),
    confirmText: d.t('admin.delete'),
    cancelText: d.t('dialog.cancel'),
    danger: true,
  });
  if (!ok) return;
  d.loading.value = true;
  try {
    await d.api('/v1/coplan/strategy-market/' + encodeURIComponent(entry.id), { method: 'DELETE' });
    await d.loadAll();
  } finally {
    d.loading.value = false;
  }
}

function createMarketActions(d) {
  return {
    openMarketSpec: function (entry) { return _openMarketSpec(d, entry); },
    forkMarketEntry: function (entry) { return _forkMarketEntry(d, entry); },
    deleteMarketEntry: function (entry) { return _deleteMarketEntry(d, entry); },
  };
}

function createSettingsActions(d) {
  async function saveSettings() {
    d.loading.value = true;
    try {
      await d.api('/v1/coplan/admin/settings', {
        method: 'PUT',
        body: JSON.stringify({ admin_contact: d.settingsForm.admin_contact }),
      });
      d.settings.admin_contact = d.settingsForm.admin_contact;
      UI.toast(d.t('admin.saved'), 'success');
    } finally {
      d.loading.value = false;
    }
  }

  function goPortalHome() {
    var path = window.location.pathname || '';
    window.location.href = path.indexOf('/coplan') >= 0 ? '/coplan' : '/';
  }

  return { saveSettings, goPortalHome };
}

function createLoadAllAction(d) {
  async function loadAll() {
    if (!d.token.value) return;
    try {
      var results = await Promise.all([
        fetch(window.location.origin + '/v1/coplan/status').then(function (r) { return r.json(); }),
        fetch(window.location.origin + '/v1/coplan/strategy-groups').then(function (r) { return r.json(); }),
        fetch(window.location.origin + '/v1/coplan/strategy-market').then(function (r) { return r.json(); }),
        d.api('/api/admin/plans'),
        d.api('/api/admin/models'),
        d.api('/v1/coplan/admin/settings'),
      ]);
      var statusRes = results[0];
      var groupsRes = results[1];
      var marketRes = results[2];
      var plansRes = results[3];
      var modelsRes = results[4];
      var settingsRes = results[5];

      d.groups.value = groupsRes.groups || [];
      d.groupCount.value = d.groups.value.length;
      d.marketEntries.value = marketRes.entries || [];
      d.marketCount.value = d.marketEntries.value.length;
      d.keyCount.value = (statusRes && statusRes.api_keys) || 0;
      d.routeModels.value = window.CoplanAdminUtils.buildRouteModels(d.groups.value);

      d.plans.value = plansRes.plans || [];
      d.models.value = modelsRes.models || [];

      var contact = (settingsRes.settings && settingsRes.settings.admin_contact)
        || (statusRes && statusRes.brand_title)
        || '';
      d.settings.admin_contact = contact;
      d.settingsForm.admin_contact = contact;
    } catch (e) {
      console.error(e);
    }
  }

  return { loadAll: loadAll };
}

window.CoplanAdminMarketSettingsActions = {
  createMarketActions: createMarketActions,
  createSettingsActions: createSettingsActions,
  createLoadAllAction: createLoadAllAction,
};
