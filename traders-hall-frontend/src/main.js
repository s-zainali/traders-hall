import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './assets/base.css'
import App from './App.vue'
import { router } from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
app.use(createPinia())

// Resolve the stored session BEFORE the router evaluates any guard. Otherwise
// the first navigation runs while isAuthenticated is still false, and a
// returning user gets bounced to /auth for a moment before being corrected.
await useAuthStore().init()

app.use(router)
app.mount('#app')