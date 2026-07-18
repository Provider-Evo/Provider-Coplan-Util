var API_BASE = window.location.origin;
var UI = window.CoplanUi;

function createDashboardActions(d) {
  function renderChart() {
    Vue.nextTick(function () {
      if (!d.usageChart.value || !window.CoplanCharts) return;
      d.chartInstance = window.CoplanCharts.createUsageLineChart(
        d.usageChart.value,
        d.usageData.value.map(function (item) { return item.date; }),
        d.usageData.value.map(function (item) { return item.total_requests; }),
        d.chartInstance,
        d.t('dash.usageTrend')
      );
    });
  }

  async function loadDashboard() {
    if (!d.token.value) return;
    try {
      var meRes = await d.api('/api/auth/me');
      d.me.value = meRes.user;
      var usageRes = await d.api('/api/user/usage?days=' + d.usageDays.value);
      d.activePlan.value = usageRes.activePlan || null;
      d.currentUsage.value = usageRes.currentPeriodUsage || null;
      d.totalUsage.value = usageRes.total || null;
      d.usageData.value = usageRes.usage || [];
      var keysRes = await d.api('/api/user/api-keys');
      d.myKeys.value = keysRes.keys || [];
      var plansRes = await d.api('/api/user/plans');
      d.planHistory.value = plansRes.plans || [];
      await d.loadStrategies();
      renderChart();
    } catch (e) {
      console.error(e);
      if (String(e.message).indexOf('令牌') >= 0 || String(e.message).indexOf('登录') >= 0) {
        d.doLogout();
      }
    }
  }

  async function loadUsage() {
    await loadDashboard();
  }

  return { loadDashboard, loadUsage, renderChart: renderChart };
}

async function postAuthForm(url, body) {
  var res = await fetch(API_BASE + url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}

function createLoginActions(d) {
  async function doLogin() {
    d.loading.value = true;
    d.authError.value = '';
    try {
      var data = await postAuthForm('/api/auth/login', d.loginForm);
      if (!data.success) {
        d.authError.value = data.error;
        return;
      }
      d.token.value = data.token;
      localStorage.setItem('ent_coplan_token', data.token);
      d.navigate('dashboard');
      await d.loadDashboard();
    } catch (e) {
      d.authError.value = e.message;
    } finally {
      d.loading.value = false;
    }
  }

  async function doRegister() {
    d.loading.value = true;
    d.authError.value = '';
    try {
      var data = await postAuthForm('/api/auth/register', d.registerForm);
      if (!data.success) {
        d.authError.value = data.error;
        return;
      }
      d.loginForm.username = d.registerForm.username;
      d.loginForm.password = d.registerForm.password;
      await doLogin();
    } catch (e) {
      d.authError.value = e.message;
    } finally {
      d.loading.value = false;
    }
  }

  return { doLogin, doRegister };
}

function createPasswordActions(d) {
  async function doChangePassword() {
    d.passwordError.value = '';
    d.passwordSuccess.value = false;
    if (!d.passwordForm.current || !d.passwordForm.new || !d.passwordForm.confirm) {
      d.passwordError.value = d.t('error.fillAll');
      return;
    }
    if (d.passwordForm.new !== d.passwordForm.confirm) {
      d.passwordError.value = d.t('error.passwordMismatch');
      return;
    }
    if (d.passwordForm.new.length < 6) {
      d.passwordError.value = d.t('error.passwordShort');
      return;
    }
    d.loading.value = true;
    try {
      await d.api('/api/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          currentPassword: d.passwordForm.current,
          newPassword: d.passwordForm.new,
        }),
      });
      d.passwordSuccess.value = true;
      d.passwordForm.current = '';
      d.passwordForm.new = '';
      d.passwordForm.confirm = '';
      UI.toast(d.t('dash.passwordOk'), 'success');
    } catch (e) {
      d.passwordError.value = e.message;
    } finally {
      d.loading.value = false;
    }
  }

  return { doChangePassword };
}

window.CoplanAppDashboardActions = {
  createDashboardActions: createDashboardActions,
  postAuthForm: postAuthForm,
  createLoginActions: createLoginActions,
  createPasswordActions: createPasswordActions,
};
