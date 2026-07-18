/**
 * Coplan Vue 组件：CoplanDialog / CoplanField / CoplanSelect
 * 通过 slot 与 placeholder 属性构建表单，替代内联 modal 与原生控件。
 */
(function () {
  'use strict';

  var _components = _buildCoplanVueUiComponents();

  window.CoplanVueUi = {
    install: function (app) {
      app.component('CoplanDialog', _components.CoplanDialog);
      app.component('coplan-dialog', _components.CoplanDialog);
      app.component('CoplanField', _components.CoplanField);
      app.component('coplan-field', _components.CoplanField);
      app.component('CoplanSelect', _components.CoplanSelect);
      app.component('coplan-select', _components.CoplanSelect);
    },
  };
})();
