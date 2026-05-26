import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'
import './styles/plex-theme.css'
import './styles/teacher-theme.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
