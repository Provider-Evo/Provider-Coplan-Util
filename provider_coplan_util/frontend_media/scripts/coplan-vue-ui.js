/**
 * Coplan Vue 组件：CoplanDialog / CoplanField / CoplanSelect
 * 通过 slot 与 placeholder 属性构建表单，替代内联 modal 与原生控件。
 */
(function () {
  'use strict';

  var CoplanDialog = {
    name: 'CoplanDialog',
    props: {
      modelValue: { type: Boolean, default: false },
      title: { type: String, default: '' },
      size: { type: String, default: 'default' },
      closable: { type: Boolean, default: true },
    },
    emits: ['update:modelValue', 'close'],
    template:
      '<div v-if="modelValue" class="coplan-ui-overlay is-visible" @click.self="onBackdrop">' +
      '  <div class="coplan-ui-dialog" :class="sizeClass" role="dialog" aria-modal="true">' +
      '    <h3 v-if="title" class="coplan-ui-dialog__title">{{ title }}</h3>' +
      '    <div class="coplan-ui-dialog__body"><slot></slot></div>' +
      '    <div v-if="$slots.footer" class="coplan-ui-dialog__footer"><slot name="footer"></slot></div>' +
      '  </div>' +
      '</div>',
    computed: {
      sizeClass: function () {
        return this.size === 'wide' ? 'coplan-ui-dialog--wide' : '';
      },
    },
    methods: {
      onBackdrop: function () {
        if (!this.closable) return;
        this.$emit('update:modelValue', false);
        this.$emit('close');
      },
      close: function () {
        this.$emit('update:modelValue', false);
        this.$emit('close');
      },
    },
  };

  var CoplanField = {
    name: 'CoplanField',
    props: {
      label: { type: String, default: '' },
      modelValue: { type: [String, Number], default: '' },
      type: { type: String, default: 'text' },
      placeholder: { type: String, default: '' },
      readonly: { type: Boolean, default: false },
      rows: { type: [String, Number], default: 4 },
      inputClass: { type: String, default: '' },
    },
    emits: ['update:modelValue'],
    template:
      '<div class="coplan-field">' +
      '  <label v-if="label" class="coplan-label">{{ label }}</label>' +
      '  <textarea v-if="type === \'textarea\'" class="coplan-textarea" :class="inputClass"' +
      '    :rows="rows" :placeholder="placeholder" :readonly="readonly"' +
      '    :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)"></textarea>' +
      '  <input v-else class="coplan-input" :class="inputClass" :type="type"' +
      '    :placeholder="placeholder" :readonly="readonly"' +
      '    :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' +
      '</div>',
  };

  var CoplanSelect = {
    name: 'CoplanSelect',
    props: {
      label: { type: String, default: '' },
      modelValue: { type: [String, Number], default: '' },
    },
    emits: ['update:modelValue', 'change'],
    template:
      '<div class="coplan-field">' +
      '  <label v-if="label" class="coplan-label">{{ label }}</label>' +
      '  <select class="coplan-select btn-sm" :value="modelValue"' +
      '    @change="onChange($event)"><slot></slot></select>' +
      '</div>',
    methods: {
      onChange: function (e) {
        this.$emit('update:modelValue', e.target.value);
        this.$emit('change', e);
      },
    },
  };

  window.CoplanVueUi = {
    install: function (app) {
      app.component('CoplanDialog', CoplanDialog);
      app.component('CoplanField', CoplanField);
      app.component('CoplanSelect', CoplanSelect);
    },
  };
})();
