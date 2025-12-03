// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'

import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'

import './style.css'

const toastOptions = {
  position: 'top-right',
  timeout: 2500,
  closeOnClick: true,
  pauseOnHover: true,
  draggable: true,
  hideProgressBar: false,
  toastClassName: 'pvz-toast',
}

createApp(App)
  .use(router)
  .use(Toast, toastOptions)
  .mount('#app')
