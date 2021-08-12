import 'jquery/dist/jquery.js';
import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';
import 'bootstrap-datepicker/dist/js/bootstrap-datepicker.js';
import 'bootstrap-datepicker/dist/css/bootstrap-datepicker3.css'

import { createApp, h } from 'vue';

import './css/main.scss';

import ResourceSelect from './js/components/ResourceSelect.vue';
import ResourceTable from './js/components/ResourceTable.vue';
import DatePicker from './js/components/DatePickerField.vue';

window.createResourceSelect = (selector, name, options, initialSelection) => {
  const app = createApp({
    render: () => h(ResourceSelect, { name, options, initialSelection }),
  });

  app.mount(selector);
};

window.createResourceTable = ({ mount, fieldName, rows, resourceType }) => {
  createApp({
    render: () => h(ResourceTable, { fieldName, resourceType, rows }),
  }).mount(mount);
};

window.createDatePicker = (mount, props) => {
  createApp({
    render: () => h(DatePicker, props),
  }).mount(mount);
};
