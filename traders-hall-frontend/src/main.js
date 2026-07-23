import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './assets/base.css'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())   // must come before mount, and before any store is used
app.mount('#app')