import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';

import { createApp, h } from 'vue';

import './css/main.scss';

import ResourceSelect from './js/components/ResourceSelect.vue';
import ResourceTable from './js/components/ResourceTable.vue';

window.createResourceSelect = (selector, name, options) => {
  const app = createApp({
    render: () => h(ResourceSelect, { name, options }),
  });

  app.mount(selector);
};

window.createResourceTable = ({ mount, fieldName, rows, resourceType }) => {
  createApp({
    render: () => h(ResourceTable, { fieldName, resourceType, rows }),
  }).mount(mount);
};
