const { createApp, ref, reactive, onMounted } = Vue;

const AdminUtils = window.CoplanAdminUtils;
const GroupActions = window.CoplanAdminGroupActions;
const PlanModelActions = window.CoplanAdminPlanModelActions;
const MarketSettingsActions = window.CoplanAdminMarketSettingsActions;

function _createAdminCoreState() {
  return {
    token: ref(localStorage.getItem('ent_coplan_admin_token') || ''),
    loading: ref(false),
    page: ref('dashboard'),
    sidebarCollapsed: ref(false),
    loginError: ref(''),
    loginForm: reactive({ username: '', password: '' }),

    groups: ref([]),
    plans: ref([]),
    models: ref([]),
    marketEntries: ref([]),
    routeModels: ref([]),
    groupCount: ref(0),
    marketCount: ref(0),
    keyCount: ref(0),
    settings: reactive({ admin_contact: '' }),
    settingsForm: reactive({ admin_contact: '' }),

    newGroupName: ref(''),
    newGroupDesc: ref(''),
  };
}

function _createAdminModalState() {
  return {
    showCodeModal: ref(false),
    codeTarget: ref(null),
    strategyCode: ref(''),
    compiledSpecText: ref(''),
    codeReadonly: ref(false),

    showKeysModal: ref(false),
    keysTarget: ref(null),
    userKeys: ref([]),
    newKey: ref(''),

    showPlanModal: ref(false),
    editingPlan: ref(null),
    planForm: reactive({
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
    }),

    showModelModal: ref(false),
    modelForm: reactive({
      model_id: '',
      display_name: '',
      description: '',
      sort_order: 0,
    }),

    showMarketSpecModal: ref(false),
    marketSpecTarget: ref(null),
    marketSpecText: ref(''),
  };
}

function createAdminState() {
  return Object.assign({}, _createAdminCoreState(), _createAdminModalState());
}

function buildAdminGroups(ctx, s, loadAll) {
  const groupCrudActions = GroupActions.createGroupCrudActions({
    api: ctx.api, t: ctx.t, loading: s.loading, newGroupName: s.newGroupName, newGroupDesc: s.newGroupDesc,
    loadAll: loadAll,
  });
  Object.assign(groupCrudActions, GroupActions.createGroupCreateAction({
    api: ctx.api, newGroupName: s.newGroupName, newGroupDesc: s.newGroupDesc, loading: s.loading, loadAll: loadAll,
  }));

  const groupCodeActions = GroupActions.createGroupCodeActions({
    api: ctx.api, t: ctx.t, loading: s.loading, codeTarget: s.codeTarget, codeReadonly: s.codeReadonly,
    strategyCode: s.strategyCode, compiledSpecText: s.compiledSpecText, showCodeModal: s.showCodeModal,
    loadAll: loadAll,
  });

  const groupKeyActions = GroupActions.createGroupKeyActions({
    api: ctx.api, t: ctx.t, loading: s.loading, groups: s.groups, keysTarget: s.keysTarget,
    newKey: s.newKey, showKeysModal: s.showKeysModal, userKeys: s.userKeys, loadAll: loadAll,
  });

  return { groupCrudActions, groupCodeActions, groupKeyActions };
}

function buildAdminPlanModelGroups(ctx, s, loadAll) {
  const planModalActions = PlanModelActions.createPlanModalActions({
    editingPlan: s.editingPlan, planForm: s.planForm, showPlanModal: s.showPlanModal,
  });

  const planActions = PlanModelActions.createPlanActions({
    api: ctx.api, t: ctx.t, loading: s.loading, editingPlan: s.editingPlan, planForm: s.planForm,
    showPlanModal: s.showPlanModal, loadAll: loadAll,
  });

  const modelActions = PlanModelActions.createModelActions({
    api: ctx.api, t: ctx.t, loading: s.loading, modelForm: s.modelForm, showModelModal: s.showModelModal,
    loadAll: loadAll,
  });

  return { planModalActions, planActions, modelActions };
}

function buildAdminMarketSettingsGroups(ctx, s, loadAll) {
  const marketActions = MarketSettingsActions.createMarketActions({
    api: ctx.api, t: ctx.t, loading: s.loading, marketSpecTarget: s.marketSpecTarget,
    marketSpecText: s.marketSpecText, showMarketSpecModal: s.showMarketSpecModal, loadAll: loadAll,
  });

  const settingsActions = MarketSettingsActions.createSettingsActions({
    api: ctx.api, t: ctx.t, loading: s.loading, settings: s.settings, settingsForm: s.settingsForm,
  });

  return { marketActions, settingsActions };
}

function buildAdminExposed(ctx, s, groups) {
  return {
    locale: ctx.locale, t: ctx.t, toggleLocale: ctx.toggleLocale,
    token: s.token, loading: s.loading, page: s.page, sidebarCollapsed: s.sidebarCollapsed,
    loginError: s.loginError, loginForm: s.loginForm,
    groups: s.groups, plans: s.plans, models: s.models, marketEntries: s.marketEntries, routeModels: s.routeModels,
    groupCount: s.groupCount, marketCount: s.marketCount, keyCount: s.keyCount, settings: s.settings, settingsForm: s.settingsForm,
    newGroupName: s.newGroupName, newGroupDesc: s.newGroupDesc,
    showCodeModal: s.showCodeModal, codeTarget: s.codeTarget, strategyCode: s.strategyCode,
    compiledSpecText: s.compiledSpecText, codeReadonly: s.codeReadonly,
    showKeysModal: s.showKeysModal, keysTarget: s.keysTarget, userKeys: s.userKeys, newKey: s.newKey,
    showPlanModal: s.showPlanModal, editingPlan: s.editingPlan, planForm: s.planForm,
    showModelModal: s.showModelModal, modelForm: s.modelForm,
    showMarketSpecModal: s.showMarketSpecModal, marketSpecTarget: s.marketSpecTarget, marketSpecText: s.marketSpecText,
    doLogin: ctx.doLogin, doLogout: ctx.doLogout,
    loadAll: ctx.loadAll, parseFeatures: AdminUtils.parseFeatures, getPlanModels: AdminUtils.getPlanModels,
    createGroup: groups.groupCrudActions.createGroup, deleteGroup: groups.groupCrudActions.deleteGroup,
    publishGroup: groups.groupCrudActions.publishGroup,
    openGroupCode: groups.groupCodeActions.openGroupCode, validateStrategyCode: groups.groupCodeActions.validateStrategyCode,
    saveStrategyCode: groups.groupCodeActions.saveStrategyCode,
    openGroupKeys: groups.groupKeyActions.openGroupKeys, generateKey: groups.groupKeyActions.generateKey,
    deleteKey: groups.groupKeyActions.deleteKey,
    openPlanModal: groups.planModalActions.openPlanModal, toggleModelSelection: groups.planModalActions.toggleModelSelection,
    savePlan: groups.planActions.savePlan, deletePlan: groups.planActions.deletePlan,
    openModelModal: groups.modelActions.openModelModal, saveModel: groups.modelActions.saveModel,
    toggleModel: groups.modelActions.toggleModel, deleteModel: groups.modelActions.deleteModel,
    openMarketSpec: groups.marketActions.openMarketSpec, forkMarketEntry: groups.marketActions.forkMarketEntry,
    deleteMarketEntry: groups.marketActions.deleteMarketEntry,
    saveSettings: groups.settingsActions.saveSettings, goPortalHome: groups.settingsActions.goPortalHome,
  };
}

function _createAdminLocaleCtx() {
  const I18N = window.CoplanI18n;
  const locale = ref(I18N.getLocale());
  function t(key, vars) {
    return I18N.t(key, vars, locale.value);
  }
  function toggleLocale() {
    locale.value = I18N.setLocale(locale.value === 'en' ? 'zh' : 'en');
  }
  return { locale, t, toggleLocale };
}

function _createAdminAuthActions(s, t, loadAll) {
  function doLogin() {
    s.loading.value = true;
    s.loginError.value = '';
    return fetch(window.location.origin + '/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(s.loginForm),
    }).then(function (res) { return res.json(); }).then(function (data) {
      if (!data.success) {
        s.loginError.value = data.error;
        return;
      }
      if (data.user.role !== 'admin') {
        s.loginError.value = t('admin.needAdmin');
        return;
      }
      s.token.value = data.token;
      localStorage.setItem('ent_coplan_admin_token', data.token);
      return loadAll();
    }).catch(function (e) {
      s.loginError.value = e.message;
    }).finally(function () {
      s.loading.value = false;
    });
  }

  function doLogout() {
    s.token.value = '';
    localStorage.removeItem('ent_coplan_admin_token');
  }

  return { doLogin, doLogout };
}

function _buildAdminActionGroups(ctx, s, loadAll) {
  const groupGroups = buildAdminGroups(ctx, s, loadAll);
  const planModelGroups = buildAdminPlanModelGroups(ctx, s, loadAll);
  const marketSettingsGroups = buildAdminMarketSettingsGroups(ctx, s, loadAll);
  return Object.assign({}, groupGroups, planModelGroups, marketSettingsGroups);
}

var app = createApp({
  setup() {
    const localeCtx = _createAdminLocaleCtx();
    const { locale, t, toggleLocale } = localeCtx;

    const s = createAdminState();
    const apiClient = AdminUtils.createApiClient(s.token, locale);
    const api = apiClient.api;

    const loadAllAction = MarketSettingsActions.createLoadAllAction({
      api: api, groups: s.groups, groupCount: s.groupCount, marketEntries: s.marketEntries,
      marketCount: s.marketCount, keyCount: s.keyCount, routeModels: s.routeModels,
      plans: s.plans, models: s.models, settings: s.settings, settingsForm: s.settingsForm,
    });

    const authActions = _createAdminAuthActions(s, t, loadAllAction.loadAll);

    const ctx = {
      locale, t, toggleLocale, api,
      doLogin: authActions.doLogin, doLogout: authActions.doLogout,
      loadAll: loadAllAction.loadAll,
    };

    const groups = _buildAdminActionGroups(ctx, s, loadAllAction.loadAll);

    onMounted(function () {
      if (s.token.value) loadAllAction.loadAll();
    });

    return buildAdminExposed(ctx, s, groups);
  },
});

app.use(window.CoplanVueUi);
app.mount('#app');
