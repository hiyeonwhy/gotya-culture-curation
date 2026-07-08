import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './assets/gotya-theme.css'

createApp(App).use(createPinia()).use(router).mount('#app')
