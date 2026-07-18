const { createApp, ref, onMounted, watch } = Vue;

const Utils = window.CoplanAppUtils;
const StrategyActions = window.CoplanAppStrategyActions;
const StateMod = window.CoplanAppState;
const DashboardActions = window.CoplanAppDashboardActions;
const PublicActions = window.CoplanAppPublicActions;
const KeyActions = window.CoplanAppKeyActions;

function createStrategyActionGroups(s, ctx) {
  const strategyListActions = StrategyActions.createStrategyListActions({
    api: ctx.api, t: ctx.t, loading: s.loading, myGroups: s.myGroups, strategyPrefix: s.strategyPrefix,
  });

  const strategyCodeActions = StrategyActions.createStrategyCodeActions({
    api: ctx.api, t: ctx.t, loading: s.loading, showStrategyModal: s.showStrategyModal,
    strategyTarget: s.strategyTarget, strategyCode: s.strategyCode, compiledSpecText: s.compiledSpecText,
    loadStrategies: strategyListActions.loadStrategies,
  });

  const strategyKeyActions = StrategyActions.createStrategyKeyBindActions({
    api: ctx.api, t: ctx.t, loading: s.loading, showStrategyKeysModal: s.showStrategyKeysModal,
    strategyKeyTarget: s.strategyKeyTarget, strategyAllowedKeyIds: s.strategyAllowedKeyIds,
    loadStrategies: strategyListActions.loadStrategies,
  });

  const strategyLifecycleActions = StrategyActions.createStrategyLifecycleActions({
    api: ctx.api, t: ctx.t, loading: s.loading, loadStrategies: strategyListActions.loadStrategies,
  });

  return { strategyListActions, strategyCodeActions, strategyKeyActions, strategyLifecycleActions };
}

function createMiscActionGroups(s, ctx, dashboardActions, strategyListActions) {
  const keyActions = KeyActions.createKeyActions({
    api: ctx.api, t: ctx.t, loading: s.loading, newKey: s.newKey, showKeyModal: s.showKeyModal,
    keyLabel: s.keyLabel, keyStrategyGroupId: s.keyStrategyGroupId, keyAllowedModelsText: s.keyAllowedModelsText,
    showKeyConfigModal: s.showKeyConfigModal, keyConfigTarget: s.keyConfigTarget, keyConfigForm: s.keyConfigForm,
    myKeys: s.myKeys, loadDashboard: dashboardActions.loadDashboard,
  });
  Object.assign(keyActions, KeyActions.createKeyModalActions({
    keyLabel: s.keyLabel, keyStrategyGroupId: s.keyStrategyGroupId, keyAllowedModelsText: s.keyAllowedModelsText,
    showKeyModal: s.showKeyModal, keyConfigTarget: s.keyConfigTarget, keyConfigForm: s.keyConfigForm,
    showKeyConfigModal: s.showKeyConfigModal,
  }));

  const keyMiscActions = KeyActions.createKeyMiscActions({
    api: ctx.api, t: ctx.t, newKey: s.newKey, loadDashboard: dashboardActions.loadDashboard,
  });

  const publicActions = PublicActions.createPublicActions({
    heroTagline: s.heroTagline, agentsTitle: s.agentsTitle, advantagesTitle: s.advantagesTitle,
    pricingTitle: s.pricingTitle, faqTitle: s.faqTitle, contactHint: s.contactHint,
    adminContact: s.adminContact, agents: s.agents, advantages: s.advantages, platforms: s.platforms,
    faqs: s.faqs, publicPlans: s.publicPlans, strategyPrefix: s.strategyPrefix,
  });

  const marketActions = PublicActions.createMarketActions({
    t: ctx.t, loading: s.loading, dashTab: s.dashTab, token: s.token, api: ctx.api,
    marketEntries: s.marketEntries, showMarketEntryModal: s.showMarketEntryModal, marketEntryTarget: s.marketEntryTarget,
    loadStrategies: strategyListActions.loadStrategies,
  });

  return { keyActions, keyMiscActions, publicActions, marketActions };
}

function createAppActionGroups(s, ctx) {
  const strategyGroups = createStrategyActionGroups(s, ctx);
  const strategyListActions = strategyGroups.strategyListActions;

  const dashboardActions = DashboardActions.createDashboardActions({
    api: ctx.api, t: ctx.t, token: s.token, me: s.me, activePlan: s.activePlan, currentUsage: s.currentUsage,
    totalUsage: s.totalUsage, usageData: s.usageData, usageDays: s.usageDays,
    myKeys: s.myKeys, planHistory: s.planHistory, usageChart: s.usageChart,
    loadStrategies: strategyListActions.loadStrategies, doLogout: ctx.doLogout,
    get chartInstance() { return ctx.chartHolder.chartInstance; },
    set chartInstance(v) { ctx.chartHolder.chartInstance = v; },
  });

  const loginActions = DashboardActions.createLoginActions({
    loading: s.loading, authError: s.authError, token: s.token, loginForm: s.loginForm, registerForm: s.registerForm,
    navigate: ctx.navigate, loadDashboard: dashboardActions.loadDashboard, t: ctx.t,
  });

  const passwordActions = DashboardActions.createPasswordActions({
    loading: s.loading, passwordForm: s.passwordForm, passwordError: s.passwordError,
    passwordSuccess: s.passwordSuccess, api: ctx.api, t: ctx.t,
  });

  const misc = createMiscActionGroups(s, ctx, dashboardActions, strategyListActions);

  return Object.assign({}, strategyGroups, misc, {
    dashboardActions, loginActions, passwordActions,
  });
}

function wireAppLifecycle(s, groups) {
  watch(s.dashTab, function () {
    if (s.dashTab.value === 'usage') groups.dashboardActions.renderChart();
  });
  watch(s.token, function (val) {
    if (val) groups.dashboardActions.loadDashboard();
  });

  onMounted(function () {
    groups.publicActions.loadPublic();
    if (s.token.value) {
      s.currentPage.value = 'dashboard';
      groups.dashboardActions.loadDashboard();
    }
    window.addEventListener('coplan:theme-change', function () {
      if (s.dashTab.value === 'usage') groups.dashboardActions.renderChart();
    });
  });
}

function buildAppExposed(s, computeds, groups, ctx) {
  return {
    locale: ctx.locale, t: ctx.t, toggleLocale: ctx.toggleLocale,
    token: s.token, me: s.me, currentPage: s.currentPage, loading: s.loading, authError: s.authError, dashTab: s.dashTab,
    loginForm: s.loginForm, registerForm: s.registerForm, publicPlans: s.publicPlans, adminContact: s.adminContact,
    heroTagline: s.heroTagline, agents: s.agents, advantages: s.advantages, platforms: s.platforms,
    agentsTitle: s.agentsTitle, advantagesTitle: s.advantagesTitle,
    pricingTitle: s.pricingTitle, faqTitle: s.faqTitle, contactHint: s.contactHint, agentTrack: computeds.agentTrack,
    activePlan: s.activePlan, currentUsage: s.currentUsage, totalUsage: s.totalUsage, usageData: s.usageData, usageDays: s.usageDays,
    myKeys: s.myKeys, planHistory: s.planHistory, newKey: s.newKey, showKeyModal: s.showKeyModal, keyLabel: s.keyLabel,
    keyStrategyGroupId: s.keyStrategyGroupId, keyAllowedModelsText: s.keyAllowedModelsText,
    showKeyConfigModal: s.showKeyConfigModal, keyConfigForm: s.keyConfigForm, myGroups: s.myGroups, strategyPrefix: s.strategyPrefix,
    showStrategyModal: s.showStrategyModal, strategyTarget: s.strategyTarget, strategyCode: s.strategyCode, compiledSpecText: s.compiledSpecText,
    showStrategyKeysModal: s.showStrategyKeysModal, strategyKeyTarget: s.strategyKeyTarget, strategyAllowedKeyIds: s.strategyAllowedKeyIds,
    usageChart: s.usageChart,
    faqs: s.faqs, monthUsagePercent: computeds.monthUsagePercent, fiveHourUsagePercent: computeds.fiveHourUsagePercent,
    revealedKeys: s.revealedKeys,
    passwordForm: s.passwordForm, passwordError: s.passwordError, passwordSuccess: s.passwordSuccess,
    marketEntries: s.marketEntries, showMarketEntryModal: s.showMarketEntryModal, marketEntryTarget: s.marketEntryTarget,
    navigate: ctx.navigate,
    doLogin: groups.loginActions.doLogin, doRegister: groups.loginActions.doRegister, doLogout: ctx.doLogout,
    loadDashboard: groups.dashboardActions.loadDashboard, loadUsage: groups.dashboardActions.loadUsage,
    loadStrategies: groups.strategyListActions.loadStrategies, loadMarket: groups.marketActions.loadMarket,
    createStrategyGroup: groups.strategyListActions.createStrategyGroup,
    openStrategyEditor: groups.strategyCodeActions.openStrategyEditor,
    validateStrategyCode: groups.strategyCodeActions.validateStrategyCode,
    saveStrategyCode: groups.strategyCodeActions.saveStrategyCode,
    openStrategyKeyBind: groups.strategyKeyActions.openStrategyKeyBind,
    toggleStrategyKey: groups.strategyKeyActions.toggleStrategyKey,
    saveStrategyKeyBind: groups.strategyKeyActions.saveStrategyKeyBind,
    publishStrategy: groups.strategyLifecycleActions.publishStrategy,
    deleteStrategy: groups.strategyLifecycleActions.deleteStrategy,
    openKeyConfig: groups.keyActions.openKeyConfig,
    saveKeyConfig: groups.keyActions.saveKeyConfig,
    viewMarketEntry: groups.marketActions.viewMarketEntry,
    forkMarketEntry: groups.marketActions.forkMarketEntry,
    parseFeatures: Utils.parseFeatures, progressClass: Utils.progressClass, formatNumber: Utils.formatNumber,
    showGenerateKey: groups.keyActions.showGenerateKey,
    doGenerateKey: groups.keyActions.doGenerateKey,
    revokeMyKey: groups.keyMiscActions.revokeMyKey,
    maskKey: Utils.maskKey, copyText: groups.keyMiscActions.copyText,
    doChangePassword: groups.passwordActions.doChangePassword,
  };
}

var app = createApp({
  setup() {
    const I18N = window.CoplanI18n;
    const locale = ref(I18N.getLocale());
    function t(key, vars) {
      return I18N.t(key, vars, locale.value);
    }
    function toggleLocale() {
      locale.value = I18N.setLocale(locale.value === 'en' ? 'zh' : 'en');
    }

    const s = StateMod.createAppState();
    const chartHolder = { chartInstance: null };
    const computeds = StateMod.createAppComputeds(s);
    const apiClient = Utils.createApiClient(s.token, locale);
    const api = apiClient.api;

    function navigate(page) {
      s.currentPage.value = page;
    }

    function doLogout() {
      s.token.value = '';
      s.me.value = null;
      localStorage.removeItem('ent_coplan_token');
      navigate('home');
    }

    const ctx = { locale, t, toggleLocale, api, navigate, doLogout, chartHolder };
    const groups = createAppActionGroups(s, ctx);
    wireAppLifecycle(s, groups);

    return buildAppExposed(s, computeds, groups, ctx);
  },
});

app.use(window.CoplanVueUi);
app.mount('#app');
