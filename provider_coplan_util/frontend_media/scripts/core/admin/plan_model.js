var UI = window.CoplanUi;
var parseFeatures = window.CoplanAdminUtils.parseFeatures;
var getPlanModels = window.CoplanAdminUtils.getPlanModels;

function fillPlanForm(planForm, p) {
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
      name: '', price: 0, requests_per_5h: 120, requests_per_month: 6000,
      description: '', featuresText: '', selectedModels: [],
      strategy_id: '', entry_alias: '', is_active: true,
    });
  }
}

function createPlanModalActions(d) {
  function openPlanModal(p) {
    d.editingPlan.value = p || null;
    fillPlanForm(d.planForm, p);
    d.showPlanModal.value = true;
  }

  function toggleModelSelection(id) {
    var index = d.planForm.selectedModels.indexOf(id);
    if (index >= 0) d.planForm.selectedModels.splice(index, 1);
    else d.planForm.selectedModels.push(id);
  }

  return { openPlanModal, toggleModelSelection };
}

function buildPlanBody(planForm) {
  return {
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
}

function createPlanActions(d) {
  async function savePlan() {
    if (!d.planForm.name) return;
    d.loading.value = true;
    try {
      var body = buildPlanBody(d.planForm);
      if (d.editingPlan.value) {
        await d.api('/api/admin/plans/' + encodeURIComponent(d.editingPlan.value.id), {
          method: 'PUT',
          body: JSON.stringify(body),
        });
      } else {
        await d.api('/api/admin/plans', { method: 'POST', body: JSON.stringify(body) });
      }
      d.showPlanModal.value = false;
      await d.loadAll();
      UI.toast(d.t('admin.saved'), 'success');
    } finally {
      d.loading.value = false;
    }
  }

  async function deletePlan(p) {
    var ok = await UI.confirm(d.t('admin.deletePlanConfirm', { name: p.name }), {
      title: d.t('dialog.confirmTitle'),
      confirmText: d.t('admin.delete'),
      cancelText: d.t('dialog.cancel'),
      danger: true,
    });
    if (!ok) return;
    d.loading.value = true;
    try {
      await d.api('/api/admin/plans/' + encodeURIComponent(p.id), { method: 'DELETE' });
      await d.loadAll();
    } finally {
      d.loading.value = false;
    }
  }

  return { savePlan, deletePlan };
}

function createModelToggleDeleteActions(d) {
  async function toggleModel(m) {
    d.loading.value = true;
    try {
      await d.api('/api/admin/models/' + encodeURIComponent(m.model_id) + '/toggle', {
        method: 'POST',
        body: JSON.stringify({ is_active: !m.is_active }),
      });
      await d.loadAll();
    } finally {
      d.loading.value = false;
    }
  }

  async function deleteModel(m) {
    var ok = await UI.confirm(d.t('admin.deleteModelConfirm', { name: m.model_id }), {
      title: d.t('dialog.confirmTitle'),
      confirmText: d.t('admin.delete'),
      cancelText: d.t('dialog.cancel'),
      danger: true,
    });
    if (!ok) return;
    d.loading.value = true;
    try {
      await d.api('/api/admin/models/' + encodeURIComponent(m.model_id), { method: 'DELETE' });
      await d.loadAll();
    } finally {
      d.loading.value = false;
    }
  }

  return { toggleModel, deleteModel };
}

function createModelActions(d) {
  function openModelModal() {
    Object.assign(d.modelForm, { model_id: '', display_name: '', description: '', sort_order: 0 });
    d.showModelModal.value = true;
  }

  async function saveModel() {
    if (!d.modelForm.model_id || !d.modelForm.display_name) return;
    d.loading.value = true;
    try {
      await d.api('/api/admin/models', { method: 'POST', body: JSON.stringify(d.modelForm) });
      d.showModelModal.value = false;
      await d.loadAll();
      UI.toast(d.t('admin.saved'), 'success');
    } finally {
      d.loading.value = false;
    }
  }

  var toggleDelete = createModelToggleDeleteActions(d);

  return {
    openModelModal,
    saveModel,
    toggleModel: toggleDelete.toggleModel,
    deleteModel: toggleDelete.deleteModel,
  };
}

window.CoplanAdminPlanModelActions = {
  fillPlanForm: fillPlanForm,
  createPlanModalActions: createPlanModalActions,
  buildPlanBody: buildPlanBody,
  createPlanActions: createPlanActions,
  createModelActions: createModelActions,
};
