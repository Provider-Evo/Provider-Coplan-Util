function createAppCoreState() {
  return {
    token: Vue.ref(localStorage.getItem('ent_coplan_token') || ''),
    me: Vue.ref(null),
    currentPage: Vue.ref('home'),
    loading: Vue.ref(false),
    authError: Vue.ref(''),
    dashTab: Vue.ref('overview'),
    loginForm: Vue.reactive({ username: '', password: '' }),
    registerForm: Vue.reactive({ username: '', email: '', password: '' }),

    publicPlans: Vue.ref([]),
    adminContact: Vue.ref(''),
    heroTagline: Vue.ref(''),
    agents: Vue.ref([]),
    advantages: Vue.ref([]),
    platforms: Vue.ref([]),
    agentsTitle: Vue.ref(''),
    advantagesTitle: Vue.ref(''),
    pricingTitle: Vue.ref(''),
    faqTitle: Vue.ref(''),
    contactHint: Vue.ref(''),

    activePlan: Vue.ref(null),
    currentUsage: Vue.ref(null),
    totalUsage: Vue.ref(null),
    usageData: Vue.ref([]),
    usageDays: Vue.ref(30),
    passwordForm: Vue.reactive({ current: '', new: '', confirm: '' }),
    passwordError: Vue.ref(''),
    passwordSuccess: Vue.ref(false),
  };
}

function createAppKeyStrategyState() {
  return {
    myKeys: Vue.ref([]),
    planHistory: Vue.ref([]),
    newKey: Vue.ref(''),
    showKeyModal: Vue.ref(false),
    keyLabel: Vue.ref(''),
    keyStrategyGroupId: Vue.ref(''),
    keyAllowedModelsText: Vue.ref(''),
    showKeyConfigModal: Vue.ref(false),
    keyConfigTarget: Vue.ref(null),
    keyConfigForm: Vue.reactive({
      strategy_group_id: '',
      allowed_models_text: '',
    }),
    myGroups: Vue.ref([]),
    strategyPrefix: Vue.ref('strategy/'),
    showStrategyModal: Vue.ref(false),
    strategyTarget: Vue.ref(null),
    strategyCode: Vue.ref(''),
    compiledSpecText: Vue.ref(''),
    showStrategyKeysModal: Vue.ref(false),
    strategyKeyTarget: Vue.ref(null),
    strategyAllowedKeyIds: Vue.ref([]),
    usageChart: Vue.ref(null),
    revealedKeys: Vue.ref([]),
    marketEntries: Vue.ref([]),
    showMarketEntryModal: Vue.ref(false),
    marketEntryTarget: Vue.ref(null),
    faqs: Vue.reactive([]),
  };
}

function createAppState() {
  return Object.assign({}, createAppCoreState(), createAppKeyStrategyState());
}

function createAppComputeds(s) {
  const agentTrack = Vue.computed(function () {
    var list = s.agents.value || [];
    if (!list.length) return [];
    return list.concat(list);
  });

  const monthUsagePercent = Vue.computed(function () {
    if (!s.activePlan.value || !s.currentUsage.value) return 0;
    var cap = s.activePlan.value.requests_per_month || 1;
    return (s.currentUsage.value.requests_month / cap) * 100;
  });

  const fiveHourUsagePercent = Vue.computed(function () {
    if (!s.activePlan.value || !s.currentUsage.value) return 0;
    var cap = s.activePlan.value.requests_per_5h || 1;
    return (s.currentUsage.value.requests_5h / cap) * 100;
  });

  return { agentTrack, monthUsagePercent, fiveHourUsagePercent };
}

window.CoplanAppState = {
  createAppCoreState: createAppCoreState,
  createAppKeyStrategyState: createAppKeyStrategyState,
  createAppState: createAppState,
  createAppComputeds: createAppComputeds,
};
