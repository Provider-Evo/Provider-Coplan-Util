const { createApp, ref, reactive, onMounted, computed, watch, nextTick } = Vue;
const API_BASE = window.location.origin;
const I18N = window.CoplanI18n;
const UI = window.CoplanUi;

var app = createApp({
  setup() {
    const locale = ref(I18N.getLocale());
    function t(key, vars) {
      return I18N.t(key, vars, locale.value);
    }
    function toggleLocale() {
      locale.value = I18N.setLocale(locale.value === 'en' ? 'zh' : 'en');
    }

    const token = ref(localStorage.getItem('ent_coplan_token') || '');
    const me = ref(null);
    const currentPage = ref('home');
    const loading = ref(false);
    const authError = ref('');
    const dashTab = ref('overview');
    const loginForm = reactive({ username: '', password: '' });
    const registerForm = reactive({ username: '', email: '', password: '' });

    const publicPlans = ref([]);
    const adminContact = ref('');
    const heroTagline = ref('');
    const agents = ref([]);
    const advantages = ref([]);
    const platforms = ref([]);
    const agentsTitle = ref('');
    const advantagesTitle = ref('');
    const pricingTitle = ref('');
    const faqTitle = ref('');
    const contactHint = ref('');

    const activePlan = ref(null);
    const currentUsage = ref(null);
    const totalUsage = ref(null);
    const usageData = ref([]);
    const usageDays = ref(30);
    const myKeys = ref([]);
    const planHistory = ref([]);
    const newKey = ref('');
    const showKeyModal = ref(false);
    const keyLabel = ref('');
    const keyStrategyGroupId = ref('');
    const keyAllowedModelsText = ref('');
    const showKeyConfigModal = ref(false);
    const keyConfigTarget = ref(null);
    const keyConfigForm = reactive({
      strategy_group_id: '',
      allowed_models_text: '',
    });
    const myGroups = ref([]);
    const strategyPrefix = ref('strategy/');
    const showStrategyModal = ref(false);
    const strategyTarget = ref(null);
    const strategyCode = ref('');
    const compiledSpecText = ref('');
    const showStrategyKeysModal = ref(false);
    const strategyKeyTarget = ref(null);
    const strategyAllowedKeyIds = ref([]);
    const usageChart = ref(null);
    const revealedKeys = ref([]);
    const passwordForm = reactive({ current: '', new: '', confirm: '' });
    const passwordError = ref('');
    const passwordSuccess = ref(false);
    const marketEntries = ref([]);
    const showMarketEntryModal = ref(false);
    const marketEntryTarget = ref(null);
    let chartInstance = null;

    const faqs = reactive([]);

    const agentTrack = computed(function () {
      var list = agents.value || [];
      if (!list.length) return [];
      return list.concat(list);
    });

    const monthUsagePercent = computed(function () {
      if (!activePlan.value || !currentUsage.value) return 0;
      var cap = activePlan.value.requests_per_month || 1;
      return (currentUsage.value.requests_month / cap) * 100;
    });

    const fiveHourUsagePercent = computed(function () {
      if (!activePlan.value || !currentUsage.value) return 0;
      var cap = activePlan.value.requests_per_5h || 1;
      return (currentUsage.value.requests_5h / cap) * 100;
    });

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

    function navigate(page) {
      currentPage.value = page;
    }

    function applyPublicPayload(payload) {
      if (!payload || typeof payload !== 'object') return;
      heroTagline.value = payload.hero_tagline || heroTagline.value;
      agentsTitle.value = payload.agents_title || agentsTitle.value;
      advantagesTitle.value = payload.advantages_title || advantagesTitle.value;
      pricingTitle.value = payload.pricing_title || pricingTitle.value;
      faqTitle.value = payload.faq_title || faqTitle.value;
      contactHint.value = payload.contact_hint || contactHint.value;
      adminContact.value = payload.admin_contact || adminContact.value;
      agents.value = Array.isArray(payload.agents) ? payload.agents : [];
      advantages.value = Array.isArray(payload.advantages) ? payload.advantages : [];
      platforms.value = Array.isArray(payload.platforms) ? payload.platforms : [];
      if (Array.isArray(payload.faqs) && payload.faqs.length) {
        faqs.splice(0, faqs.length);
        payload.faqs.forEach(function (item) {
          faqs.push({ q: item.q, a: item.a, open: false });
        });
      }
    }

    async function loadPublic() {
      try {
        var results = await Promise.all([
          fetch(API_BASE + '/v1/coplan/public').then(function (r) { return r.json(); }),
          fetch(API_BASE + '/v1/coplan/market/templates').then(function (r) { return r.json(); }),
          fetch(API_BASE + '/v1/coplan/status').then(function (r) { return r.json(); }),
        ]);
        var publicRes = results[0];
        var marketRes = results[1];
        var statusRes = results[2];
        applyPublicPayload(publicRes);
        if (statusRes && statusRes.hero_tagline) {
          heroTagline.value = statusRes.hero_tagline;
        }
        if (statusRes && statusRes.brand_title && !publicRes.admin_contact) {
          adminContact.value = statusRes.brand_title;
        }
        if (statusRes && statusRes.strategy_prefix) {
          strategyPrefix.value = statusRes.strategy_prefix;
        }
        publicPlans.value = (publicRes.plans || marketRes.plans || []).map(function (tpl) {
          return {
            id: tpl.id,
            name: tpl.name,
            price: tpl.price != null ? tpl.price : 0,
            description: tpl.description,
            requests_per_5h: tpl.requests_per_5h || 120,
            requests_per_month: tpl.requests_per_month || 6000,
            features: typeof tpl.features === 'string' ? tpl.features : JSON.stringify(Array.isArray(tpl.features) ? tpl.features : []),
          };
        });
      } catch (e) {
        console.debug('loadPublic:', e);
      }
    }

    async function loadMarket() {
      try {
        var res = await fetch(API_BASE + '/v1/coplan/strategy-market');
        var data = await res.json();
        marketEntries.value = data.entries || [];
      } catch (e) {
        console.error(e);
      }
    }

    function viewMarketEntry(entry) {
      marketEntryTarget.value = entry;
      showMarketEntryModal.value = true;
    }

    async function forkMarketEntry(entry) {
      if (!entry || !token.value) return;
      loading.value = true;
      try {
        var res = await api('/api/user/strategy-groups/fork', {
          method: 'POST',
          body: JSON.stringify({ market_entry_id: entry.id }),
        });
        showMarketEntryModal.value = false;
        await loadStrategies();
        dashTab.value = 'strategies';
        UI.toast(t('dash.marketForkOk'), 'success');
      } catch (e) {
        await UI.alert(String(e.message || e), { title: t('dialog.errorTitle') });
      } finally {
        loading.value = false;
      }
    }

    async function loadDashboard() {
      if (!token.value) return;
      try {
        var meRes = await api('/api/auth/me');
        me.value = meRes.user;
        var usageRes = await api('/api/user/usage?days=' + usageDays.value);
        activePlan.value = usageRes.activePlan || null;
        currentUsage.value = usageRes.currentPeriodUsage || null;
        totalUsage.value = usageRes.total || null;
        usageData.value = usageRes.usage || [];
        var keysRes = await api('/api/user/api-keys');
        myKeys.value = keysRes.keys || [];
        var plansRes = await api('/api/user/plans');
        planHistory.value = plansRes.plans || [];
        await loadStrategies();
        renderChart();
      } catch (e) {
        console.error(e);
        if (String(e.message).indexOf('令牌') >= 0 || String(e.message).indexOf('登录') >= 0) {
          doLogout();
        }
      }
    }

    async function doLogin() {
      loading.value = true;
      authError.value = '';
      try {
        var res = await fetch(API_BASE + '/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(loginForm),
        });
        var data = await res.json();
        if (!data.success) {
          authError.value = data.error;
          return;
        }
        token.value = data.token;
        localStorage.setItem('ent_coplan_token', data.token);
        navigate('dashboard');
        await loadDashboard();
      } catch (e) {
        authError.value = e.message;
      } finally {
        loading.value = false;
      }
    }

    async function doRegister() {
      loading.value = true;
      authError.value = '';
      try {
        var res = await fetch(API_BASE + '/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(registerForm),
        });
        var data = await res.json();
        if (!data.success) {
          authError.value = data.error;
          return;
        }
        loginForm.username = registerForm.username;
        loginForm.password = registerForm.password;
        await doLogin();
      } catch (e) {
        authError.value = e.message;
      } finally {
        loading.value = false;
      }
    }

    function doLogout() {
      token.value = '';
      me.value = null;
      localStorage.removeItem('ent_coplan_token');
      navigate('home');
    }

    function parseFeatures(f) {
      try {
        return JSON.parse(f);
      } catch (e) {
        return f ? String(f).split('\n').filter(Boolean) : [];
      }
    }

    function progressClass(pct) {
      if (pct >= 90) return 'progress-red';
      if (pct >= 70) return 'progress-yellow';
      return 'progress-green';
    }

    function formatNumber(n) {
      if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
      if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
      return String(n);
    }

    function parseModelsText(text) {
      return String(text || '').split(/[\n,]/).map(function (s) { return s.trim(); }).filter(Boolean);
    }

    async function loadStrategies() {
      if (!token.value) return;
      try {
        var res = await api('/api/user/strategy-groups');
        myGroups.value = res.groups || [];
        if (res.strategy_prefix) strategyPrefix.value = res.strategy_prefix;
      } catch (e) {
        console.error(e);
      }
    }

    async function createStrategyGroup() {
      var name = await UI.prompt(t('dash.strategyName'), { placeholder: 'my-routing', title: t('dash.strategyCreate') });
      if (!name) return;
      loading.value = true;
      try {
        await api('/api/user/strategy-groups', {
          method: 'POST',
          body: JSON.stringify({ name: name }),
        });
        await loadStrategies();
        UI.toast(t('admin.saved'), 'success');
      } catch (e) {
        await UI.alert(String(e.message || e), { title: t('dialog.errorTitle') });
      } finally {
        loading.value = false;
      }
    }

    async function openStrategyEditor(g) {
      strategyTarget.value = g;
      loading.value = true;
      try {
        var res = await api('/api/user/strategy-groups/' + encodeURIComponent(g.id) + '/code');
        strategyCode.value = res.source_code || '';
        compiledSpecText.value = JSON.stringify(res.compiled_spec || {}, null, 2);
        showStrategyModal.value = true;
      } finally {
        loading.value = false;
      }
    }

    async function validateStrategyCode() {
      loading.value = true;
      try {
        var res = await api('/api/user/strategy-groups/compile', {
          method: 'POST',
          body: JSON.stringify({ source_code: strategyCode.value }),
        });
        compiledSpecText.value = JSON.stringify(res.spec || {}, null, 2);
        UI.toast(t('dash.strategyValidated'), 'success');
      } catch (e) {
        await UI.alert(String(e.message || e), { title: t('dialog.errorTitle') });
      } finally {
        loading.value = false;
      }
    }

    async function saveStrategyCode() {
      if (!strategyTarget.value) return;
      loading.value = true;
      try {
        await api('/api/user/strategy-groups/' + encodeURIComponent(strategyTarget.value.id) + '/code', {
          method: 'PUT',
          body: JSON.stringify({ source_code: strategyCode.value }),
        });
        showStrategyModal.value = false;
        await loadStrategies();
        UI.toast(t('dash.strategySaved'), 'success');
      } catch (e) {
        await UI.alert(String(e.message || e), { title: t('dialog.errorTitle') });
      } finally {
        loading.value = false;
      }
    }

    function openStrategyKeyBind(g) {
      strategyKeyTarget.value = g;
      strategyAllowedKeyIds.value = (g.allowed_key_ids || []).slice();
      showStrategyKeysModal.value = true;
    }

    function toggleStrategyKey(id) {
      var index = strategyAllowedKeyIds.value.indexOf(id);
      if (index >= 0) strategyAllowedKeyIds.value.splice(index, 1);
      else strategyAllowedKeyIds.value.push(id);
    }

    async function saveStrategyKeyBind() {
      if (!strategyKeyTarget.value) return;
      loading.value = true;
      try {
        await api('/api/user/strategy-groups/' + encodeURIComponent(strategyKeyTarget.value.id) + '/keys', {
          method: 'PUT',
          body: JSON.stringify({ key_ids: strategyAllowedKeyIds.value }),
        });
        showStrategyKeysModal.value = false;
        await loadStrategies();
        UI.toast(t('admin.saved'), 'success');
      } finally {
        loading.value = false;
      }
    }

    async function publishStrategy(g) {
      loading.value = true;
      try {
        await api('/api/user/strategy-groups/' + encodeURIComponent(g.id) + '/publish', {
          method: 'POST',
          body: JSON.stringify({ title: g.name, description: g.description || '' }),
        });
        UI.toast(t('dash.strategyPublished'), 'success');
      } catch (e) {
        await UI.alert(String(e.message || e), { title: t('dialog.errorTitle') });
      } finally {
        loading.value = false;
      }
    }

    async function deleteStrategy(g) {
      var ok = await UI.confirm(t('dash.strategyDeleteConfirm', { name: g.name }), {
        title: t('dialog.confirmTitle'),
        confirmText: t('admin.delete'),
        cancelText: t('dialog.cancel'),
        danger: true,
      });
      if (!ok) return;
      loading.value = true;
      try {
        await api('/api/user/strategy-groups/' + encodeURIComponent(g.id), { method: 'DELETE' });
        await loadStrategies();
      } finally {
        loading.value = false;
      }
    }

    function showGenerateKey() {
      keyLabel.value = '';
      keyStrategyGroupId.value = '';
      keyAllowedModelsText.value = '';
      showKeyModal.value = true;
    }

    function openKeyConfig(k) {
      keyConfigTarget.value = k;
      keyConfigForm.strategy_group_id = k.strategy_group_id || '';
      keyConfigForm.allowed_models_text = (k.allowed_models || []).join('\n');
      showKeyConfigModal.value = true;
    }

    async function saveKeyConfig() {
      if (!keyConfigTarget.value) return;
      loading.value = true;
      try {
        await api('/api/user/api-keys/' + encodeURIComponent(keyConfigTarget.value.id), {
          method: 'PUT',
          body: JSON.stringify({
            strategy_group_id: keyConfigForm.strategy_group_id,
            allowed_models: parseModelsText(keyConfigForm.allowed_models_text),
          }),
        });
        showKeyConfigModal.value = false;
        await loadDashboard();
        UI.toast(t('admin.saved'), 'success');
      } finally {
        loading.value = false;
      }
    }

    async function doGenerateKey() {
      loading.value = true;
      try {
        var data = await api('/api/user/api-keys', {
          method: 'POST',
          body: JSON.stringify({
            label: keyLabel.value,
            strategy_group_id: keyStrategyGroupId.value,
            allowed_models: parseModelsText(keyAllowedModelsText.value),
          }),
        });
        newKey.value = data.key;
        showKeyModal.value = false;
        await loadDashboard();
      } finally {
        loading.value = false;
      }
    }

    async function revokeMyKey(k) {
      var ok = await UI.confirm(t('dash.revokeConfirm'), {
        title: t('dialog.confirmTitle'),
        confirmText: t('dash.revoke'),
        cancelText: t('dialog.cancel'),
        danger: true,
      });
      if (!ok) return;
      await api('/api/user/api-keys/' + k.id, { method: 'DELETE' });
      newKey.value = '';
      await loadDashboard();
    }

    async function loadUsage() {
      await loadDashboard();
    }

    function maskKey(key) {
      if (!key || key.length < 12) return '***';
      return key.slice(0, 7) + '***' + key.slice(-4);
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
      UI.toast(t('dash.copied'), 'success');
    }

    async function doChangePassword() {
      passwordError.value = '';
      passwordSuccess.value = false;
      if (!passwordForm.current || !passwordForm.new || !passwordForm.confirm) {
        passwordError.value = t('error.fillAll');
        return;
      }
      if (passwordForm.new !== passwordForm.confirm) {
        passwordError.value = t('error.passwordMismatch');
        return;
      }
      if (passwordForm.new.length < 6) {
        passwordError.value = t('error.passwordShort');
        return;
      }
      loading.value = true;
      try {
        await api('/api/auth/change-password', {
          method: 'POST',
          body: JSON.stringify({
            currentPassword: passwordForm.current,
            newPassword: passwordForm.new,
          }),
        });
        passwordSuccess.value = true;
        passwordForm.current = '';
        passwordForm.new = '';
        passwordForm.confirm = '';
        UI.toast(t('dash.passwordOk'), 'success');
      } catch (e) {
        passwordError.value = e.message;
      } finally {
        loading.value = false;
      }
    }

    function renderChart() {
      nextTick(function () {
        if (!usageChart.value || !window.CoplanCharts) return;
        chartInstance = window.CoplanCharts.createUsageLineChart(
          usageChart.value,
          usageData.value.map(function (d) { return d.date; }),
          usageData.value.map(function (d) { return d.total_requests; }),
          chartInstance,
          t('dash.usageTrend')
        );
      });
    }

    watch(dashTab, function () {
      if (dashTab.value === 'usage') renderChart();
    });
    watch(token, function (val) {
      if (val) loadDashboard();
    });

    onMounted(function () {
      loadPublic();
      if (token.value) {
        navigate('dashboard');
        loadDashboard();
      }
      window.addEventListener('coplan:theme-change', function () {
        if (dashTab.value === 'usage') renderChart();
      });
    });

    return {
      locale, t, toggleLocale,
      token, me, currentPage, loading, authError, dashTab,
      loginForm, registerForm, publicPlans, adminContact, heroTagline,
      agents, advantages, platforms, agentsTitle, advantagesTitle,
      pricingTitle, faqTitle, contactHint, agentTrack,
      activePlan, currentUsage, totalUsage, usageData, usageDays,
      myKeys, planHistory, newKey, showKeyModal, keyLabel, keyStrategyGroupId, keyAllowedModelsText,
      showKeyConfigModal, keyConfigForm, myGroups, strategyPrefix,
      showStrategyModal, strategyTarget, strategyCode, compiledSpecText,
      showStrategyKeysModal, strategyKeyTarget, strategyAllowedKeyIds,
      usageChart,
      faqs, monthUsagePercent, fiveHourUsagePercent, revealedKeys,
      passwordForm, passwordError, passwordSuccess,
      marketEntries, showMarketEntryModal, marketEntryTarget,
      navigate, doLogin, doRegister, doLogout, loadDashboard, loadUsage, loadStrategies, loadMarket,
      createStrategyGroup, openStrategyEditor, validateStrategyCode, saveStrategyCode,
      openStrategyKeyBind, toggleStrategyKey, saveStrategyKeyBind,
      publishStrategy, deleteStrategy, openKeyConfig, saveKeyConfig,
      viewMarketEntry, forkMarketEntry,
      parseFeatures, progressClass, formatNumber, showGenerateKey,
      doGenerateKey, revokeMyKey, maskKey, copyText, doChangePassword,
    };
  },
});

app.use(window.CoplanVueUi);
app.mount('#app');
