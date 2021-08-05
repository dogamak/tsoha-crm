import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';

import { createApp, h } from 'vue';

import './css/main.scss';

import ResourceSelect from './js/components/ResourceSelect.vue';

window.createResourceSelect = (selector, name, options) => {
  const app = createApp({
    render: () => h(ResourceSelect, { name, options }),
  });

  app.mount(selector);
};
