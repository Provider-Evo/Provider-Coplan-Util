const { createApp, ref, reactive, onMounted } = Vue;
const API_BASE = window.location.origin;
const I18N = window.CoplanI18n;
const UI = window.CoplanUi;

function buildRouteModels(groups) {
  var rows = [];
  (groups || []).forEach(function (g) {
    var spec = g.spec || {};
    var aliases = spec.aliases || {};
    Object.keys(aliases).forEach(function (alias) {
      var block = aliases[alias] || {};
      var strategy = block.strategy || 'single';
      (block.routes || []).forEach(function (r) {
        rows.push({
          id: g.id + ':' + alias + ':' + (r.model || ''),
          alias: alias,
          strategy: strategy,
          platform: r.platform || '-',
          model: r.model || '-',
          group_name: g.name || g.id,
        });
      });
    });
    var def = spec.default;
    if (def && Array.isArray(def.routes)) {
      (def.routes || []).forEach(function (r) {
        rows.push({
          id: g.id + ':default:' + (r.model || ''),
          alias: '*',
          strategy: def.strategy || 'single',
          platform: r.platform || '-',
          model: r.model || '-',
          group_name: g.name || g.id,
        });
      });
    }
  });
  return rows;
}

var app = createApp({
  setup() {
    const locale = ref(I18N.getLocale());
    function t(key, vars) {
      return I18N.t(key, vars, locale.value);
    }
    function toggleLocale() {
      locale.value = I18N.setLocale(locale.value === 'en' ? 'zh' : 'en');
    }

    const token = ref(localStorage.getItem('ent_coplan_admin_token') || '');
    const loading = ref(false);
    const page = ref('dashboard');
    const sidebarCollapsed = ref(false);
    const loginError = ref('');
    const loginForm = reactive({ username: '', password: '' });

    const groups = ref([]);
    const plans = ref([]);
    const models = ref([]);
    const marketEntries = ref([]);
    const routeModels = ref([]);
    const groupCount = ref(0);
    const marketCount = ref(0);
    const keyCount = ref(0);
    const settings = reactive({ admin_contact: '' });
    const settingsForm = reactive({ admin_contact: '' });

    const newGroupName = ref('');
    const newGroupDesc = ref('');

    const showCodeModal = ref(false);
    const codeTarget = ref(null);
    const strategyCode = ref('');
    const compiledSpecText = ref('');
    const codeReadonly = ref(false);

    const showKeysModal = ref(false);
    const keysTarget = ref(null);
    const userKeys = ref([]);
    const newKey = ref('');

    const showPlanModal = ref(false);
    const editingPlan = ref(null);
    const planForm = reactive({
      name: '',
      price: 0,
      requests_per_5h: 0,
      requests_per_month: 0,
      description: '',
      featuresText: '',
      selectedModels: [],
      strategy_id: '',
      entry_alias: '',
      is_active: true,
    });

    const showModelModal = ref(false);
    const modelForm = reactive({
      model_id: '',
      display_name: '',
      description: '',
      sort_order: 0,
    });

    const showMarketSpecModal = ref(false);
    const marketSpecTarget = ref(null);
    const marketSpecText = ref('');

    const headers = function () {
      return { Authorization: 'Bearer ' + token.value, 'Content-Type': 'application/json' };
    };

    async function api(url, opts) {
      opts = opts || {};
      var res = await fetch(API_BASE + url, Object.assign({}, opts, {
        headers: Object.assign({}, headers(), opts.headers || {}),
      }));
      var data = await res.json();
      if (!res.ok) throw new Error(data.error || I18N.t('error.request', null, locale.value));
      return data;
    }

    async function doLogin() {
      loading.value = true;
      loginError.value = '';
      try {
        var res = await fetch(API_BASE + '/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(loginForm),
        });
        var data = await res.json();
        if (!data.success) {
          loginError.value = data.error;
          return;
        }
        if (data.user.role !== 'admin') {
          loginError.value = t('admin.needAdmin');
          return;
        }
        token.value = data.token;
        localStorage.setItem('ent_coplan_admin_token', data.token);
        await loadAll();
      } catch (e) {
        loginError.value = e.message;
      } finally {
        loading.value = false;
      }
    }

    function doLogout() {
      token.value = '';
      localStorage.removeItem('ent_coplan_admin_token');
    }

    async function loadAll() {
      if (!token.value) return;
      try {
        var results = await Promise.all([
          fetch(API_BASE + '/v1/coplan/status').then(function (r) { return r.json(); }),
          fetch(API_BASE + '/v1/coplan/strategy-groups').then(function (r) { return r.json(); }),
          fetch(API_BASE + '/v1/coplan/strategy-market').then(function (r) { return r.json(); }),
          api('/api/admin/plans'),
          api('/api/admin/models'),
          api('/v1/coplan/admin/settings'),
        ]);
        var statusRes = results[0];
        var groupsRes = results[1];
        var marketRes = results[2];
        var plansRes = results[3];
        var modelsRes = results[4];
        var settingsRes = results[5];

        groups.value = groupsRes.groups || [];
        groupCount.value = groups.value.length;
        marketEntries.value = marketRes.entries || [];
        marketCount.value = marketEntries.value.length;
        keyCount.value = (statusRes && statusRes.api_keys) || 0;
        routeModels.value = buildRouteModels(groups.value);

        plans.value = plansRes.plans || [];
        models.value = modelsRes.models || [];

        var contact = (settingsRes.settings && settingsRes.settings.admin_contact)
          || (statusRes && statusRes.brand_title)
          || '';
        settings.admin_contact = contact;
        settingsForm.admin_contact = contact;
      } catch (e) {
        console.error(e);
      }
    }

    function parseFeatures(f) {
      try {
        return JSON.parse(f);
      } catch (e) {
        return f ? String(f).split('\n').filter(Boolean) : [];
      }
    }

    function getPlanModels(p) {
      try {
        return JSON.parse(p.selected_models || '[]') || [];
      } catch (e) {
        return [];
      }
    }

    async function createGroup() {
      var name = (newGroupName.value || '').trim();
      if (!name) return;
      loading.value = true;
      try {
        await api('/v1/coplan/strategy-groups', {
          method: 'POST',
          body: JSON.stringify({ name: name, description: newGroupDesc.value || '' }),
        });
        newGroupName.value = '';
        newGroupDesc.value = '';
        await loadAll();
      } finally {
        loading.value = false;
      }
    }

    async function deleteGroup(g) {
      if (g.source === 'code') return;
      var ok = await UI.confirm(t('admin.deleteGroupConfirm', { name: g.name }), {
        title: t('dialog.confirmTitle'),
        confirmText: t('admin.delete'),
        cancelText: t('dialog.cancel'),
        danger: true,
      });
      if (!ok) return;
      loading.value = true;
      try {
        await api('/v1/coplan/strategy-groups/' + encodeURIComponent(g.id), { method: 'DELETE' });
        await loadAll();
      } finally {
        loading.value = false;
      }
    }

    async function openGroupCode(g) {
      codeTarget.value = g;
      codeReadonly.value = g.source === 'code';
      loading.value = true;
      try {
        var data = await api('/v1/coplan/strategy-groups/' + encodeURIComponent(g.id) + '/code');
        strategyCode.value = data.source_code || '';
        compiledSpecText.value = JSON.stringify(data.compiled_spec || {}, null, 2);
        showCodeModal.value = true;
      } catch (e) {
        await UI.alert(String(e.message || e), { title: t('dialog.errorTitle') });
      } finally {
        loading.value = false;
      }
    }

    async function validateStrategyCode() {
      loading.value = true;
      try {
        var data = await api('/v1/coplan/strategy-groups/compile', {
          method: 'POST',
          body: JSON.stringify({ source_code: strategyCode.value }),
        });
        compiledSpecText.value = JSON.stringify(data.spec || {}, null, 2);
        UI.toast(t('admin.strategyValidated'), 'success');
      } catch (e) {
        await UI.alert(String(e.message || e), { title: t('dialog.errorTitle') });
      } finally {
        loading.value = false;
      }
    }

    async function saveStrategyCode() {
      if (!codeTarget.value || codeReadonly.value) return;
      loading.value = true;
      try {
        await api('/v1/coplan/strategy-groups/' + encodeURIComponent(codeTarget.value.id) + '/code', {
          method: 'PUT',
          body: JSON.stringify({ source_code: strategyCode.value }),
        });
        showCodeModal.value = false;
        UI.toast(t('admin.strategySaved'), 'success');
        await loadAll();
      } catch (e) {
        await UI.alert(String(e.message || e), { title: t('dialog.errorTitle') });
      } finally {
        loading.value = false;
      }
    }

    async function publishGroup(g) {
      var ok = await UI.confirm(t('admin.publishConfirm', { name: g.name }), {
        title: t('dialog.confirmTitle'),
        confirmText: t('admin.marketPublish'),
        cancelText: t('dialog.cancel'),
      });
      if (!ok) return;
      loading.value = true;
      try {
        await api('/v1/coplan/strategy-market', {
          method: 'POST',
          body: JSON.stringify({
            group_id: g.id,
            title: g.name,
            description: g.description || '',
          }),
        });
        UI.toast(t('admin.published'), 'success');
        await loadAll();
      } catch (e) {
        await UI.alert(String(e.message || e), { title: t('dialog.errorTitle') });
      } finally {
        loading.value = false;
      }
    }

    function openGroupKeys(g) {
      keysTarget.value = g;
      newKey.value = '';
      showKeysModal.value = true;
      loadGroupKeys();
    }

    async function loadGroupKeys() {
      if (!keysTarget.value) return;
      userKeys.value = keysTarget.value.keys || [];
    }

    async function generateKey() {
      if (!keysTarget.value) return;
      loading.value = true;
      try {
        var data = await api('/v1/coplan/strategy-groups/' + encodeURIComponent(keysTarget.value.id) + '/keys', {
          method: 'POST',
          body: JSON.stringify({ label: 'admin' }),
        });
        newKey.value = data.key || (data.entry && data.entry.key) || '';
        await loadAll();
        var refreshed = groups.value.find(function (g) { return g.id === keysTarget.value.id; });
        if (refreshed) {
          keysTarget.value = refreshed;
          userKeys.value = refreshed.keys || [];
        }
      } finally {
        loading.value = false;
      }
    }

    async function deleteKey(k) {
      if (!keysTarget.value) return;
      var ok = await UI.confirm(t('admin.deleteKeyConfirm', { key: k.key || k.id }), {
        title: t('dialog.confirmTitle'),
        confirmText: t('admin.delete'),
        cancelText: t('dialog.cancel'),
        danger: true,
      });
      if (!ok) return;
      loading.value = true;
      try {
        await api('/v1/coplan/strategy-groups/' + encodeURIComponent(keysTarget.value.id) + '/keys/' + encodeURIComponent(k.id), {
          method: 'DELETE',
        });
        await loadAll();
        var refreshed = groups.value.find(function (g) { return g.id === keysTarget.value.id; });
        if (refreshed) {
          keysTarget.value = refreshed;
          userKeys.value = refreshed.keys || [];
        }
      } finally {
        loading.value = false;
      }
    }

    function openPlanModal(p) {
      editingPlan.value = p || null;
      if (p) {
        planForm.name = p.name;
        planForm.price = p.price;
        planForm.requests_per_5h = p.requests_per_5h;
        planForm.requests_per_month = p.requests_per_month;
        planForm.description = p.description || '';
        planForm.featuresText = parseFeatures(p.features).join('\n');
        planForm.selectedModels = getPlanModels(p);
        planForm.strategy_id = p.strategy_id || '';
        planForm.entry_alias = p.entry_alias || '';
        planForm.is_active = p.is_active !== false;
      } else {
        Object.assign(planForm, {
          name: '',
          price: 0,
          requests_per_5h: 120,
          requests_per_month: 6000,
          description: '',
          featuresText: '',
          selectedModels: [],
          strategy_id: '',
          entry_alias: '',
          is_active: true,
        });
      }
      showPlanModal.value = true;
    }

    function toggleModelSelection(id) {
      var index = planForm.selectedModels.indexOf(id);
      if (index >= 0) planForm.selectedModels.splice(index, 1);
      else planForm.selectedModels.push(id);
    }

    async function savePlan() {
      if (!planForm.name) return;
      loading.value = true;
      try {
        var body = {
          name: planForm.name,
          price: planForm.price,
          requests_per_5h: planForm.requests_per_5h,
          requests_per_month: planForm.requests_per_month,
          description: planForm.description,
          features: planForm.featuresText.split('\n').filter(Boolean),
          selected_models: planForm.selectedModels,
          strategy_id: planForm.strategy_id,
          entry_alias: planForm.entry_alias,
          is_active: planForm.is_active,
        };
        if (editingPlan.value) {
          await api('/api/admin/plans/' + encodeURIComponent(editingPlan.value.id), {
            method: 'PUT',
            body: JSON.stringify(body),
          });
        } else {
          await api('/api/admin/plans', { method: 'POST', body: JSON.stringify(body) });
        }
        showPlanModal.value = false;
        await loadAll();
        UI.toast(t('admin.saved'), 'success');
      } finally {
        loading.value = false;
      }
    }

    async function deletePlan(p) {
      var ok = await UI.confirm(t('admin.deletePlanConfirm', { name: p.name }), {
        title: t('dialog.confirmTitle'),
        confirmText: t('admin.delete'),
        cancelText: t('dialog.cancel'),
        danger: true,
      });
      if (!ok) return;
      loading.value = true;
      try {
        await api('/api/admin/plans/' + encodeURIComponent(p.id), { method: 'DELETE' });
        await loadAll();
      } finally {
        loading.value = false;
      }
    }

    function openModelModal() {
      Object.assign(modelForm, { model_id: '', display_name: '', description: '', sort_order: 0 });
      showModelModal.value = true;
    }

    async function saveModel() {
      if (!modelForm.model_id || !modelForm.display_name) return;
      loading.value = true;
      try {
        await api('/api/admin/models', { method: 'POST', body: JSON.stringify(modelForm) });
        showModelModal.value = false;
        await loadAll();
        UI.toast(t('admin.saved'), 'success');
      } finally {
        loading.value = false;
      }
    }

    async function toggleModel(m) {
      loading.value = true;
      try {
        await api('/api/admin/models/' + encodeURIComponent(m.model_id) + '/toggle', {
          method: 'POST',
          body: JSON.stringify({ is_active: !m.is_active }),
        });
        await loadAll();
      } finally {
        loading.value = false;
      }
    }

    async function deleteModel(m) {
      var ok = await UI.confirm(t('admin.deleteModelConfirm', { name: m.model_id }), {
        title: t('dialog.confirmTitle'),
        confirmText: t('admin.delete'),
        cancelText: t('dialog.cancel'),
        danger: true,
      });
      if (!ok) return;
      loading.value = true;
      try {
        await api('/api/admin/models/' + encodeURIComponent(m.model_id), { method: 'DELETE' });
        await loadAll();
      } finally {
        loading.value = false;
      }
    }

    async function openMarketSpec(entry) {
      marketSpecTarget.value = entry;
      loading.value = true;
      try {
        var data = await api('/v1/coplan/strategy-market/' + encodeURIComponent(entry.id));
        marketSpecText.value = (data.entry && data.entry.source_code) || '';
        if (!marketSpecText.value) {
          marketSpecText.value = JSON.stringify((data.entry && data.entry.spec) || entry.spec || {}, null, 2);
        }
        showMarketSpecModal.value = true;
      } catch (e) {
        marketSpecText.value = JSON.stringify(entry.spec || {}, null, 2);
        showMarketSpecModal.value = true;
      } finally {
        loading.value = false;
      }
    }

    async function forkMarketEntry(entry) {
      var ok = await UI.confirm(t('admin.forkConfirm', { name: entry.title }), {
        title: t('dialog.confirmTitle'),
        confirmText: t('admin.marketFork'),
        cancelText: t('dialog.cancel'),
      });
      if (!ok) return;
      loading.value = true;
      try {
        await api('/v1/coplan/strategy-market/' + encodeURIComponent(entry.id) + '/fork', {
          method: 'POST',
          body: JSON.stringify({ name: entry.title + '-fork' }),
        });
        UI.toast(t('admin.forked'), 'success');
        await loadAll();
      } catch (e) {
        await UI.alert(String(e.message || e), { title: t('dialog.errorTitle') });
      } finally {
        loading.value = false;
      }
    }

    async function deleteMarketEntry(entry) {
      var ok = await UI.confirm(t('admin.deleteMarketConfirm', { name: entry.title }), {
        title: t('dialog.confirmTitle'),
        confirmText: t('admin.delete'),
        cancelText: t('dialog.cancel'),
        danger: true,
      });
      if (!ok) return;
      loading.value = true;
      try {
        await api('/v1/coplan/strategy-market/' + encodeURIComponent(entry.id), { method: 'DELETE' });
        await loadAll();
      } finally {
        loading.value = false;
      }
    }

    async function saveSettings() {
      loading.value = true;
      try {
        await api('/v1/coplan/admin/settings', {
          method: 'PUT',
          body: JSON.stringify({ admin_contact: settingsForm.admin_contact }),
        });
        settings.admin_contact = settingsForm.admin_contact;
        UI.toast(t('admin.saved'), 'success');
      } finally {
        loading.value = false;
      }
    }

    function goPortalHome() {
      var path = window.location.pathname || '';
      window.location.href = path.indexOf('/coplan') >= 0 ? '/coplan' : '/';
    }

    onMounted(function () {
      if (token.value) loadAll();
    });

    return {
      locale, t, toggleLocale,
      token, loading, page, sidebarCollapsed, loginError, loginForm,
      groups, plans, models, marketEntries, routeModels,
      groupCount, marketCount, keyCount, settings, settingsForm,
      newGroupName, newGroupDesc,
      showCodeModal, codeTarget, strategyCode, compiledSpecText, codeReadonly,
      showKeysModal, keysTarget, userKeys, newKey,
      showPlanModal, editingPlan, planForm,
      showModelModal, modelForm,
      showMarketSpecModal, marketSpecTarget, marketSpecText,
      doLogin, doLogout, loadAll, parseFeatures, getPlanModels,
      createGroup, deleteGroup, openGroupCode, validateStrategyCode, saveStrategyCode, publishGroup,
      openGroupKeys, generateKey, deleteKey,
      openPlanModal, toggleModelSelection, savePlan, deletePlan,
      openModelModal, saveModel, toggleModel, deleteModel,
      openMarketSpec, forkMarketEntry, deleteMarketEntry,
      saveSettings, goPortalHome,
    };
  },
});

app.use(window.CoplanVueUi);
app.mount('#app');
