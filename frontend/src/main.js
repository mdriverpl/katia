import { createApp } from 'vue'
import './forest-sand.css'
import './themes.css'
import './theme.js'
import App from './App.vue'
import PublicClient from './components/PublicClient.vue'

const publicMatch = window.location.hash.match(/^#\/(?:service|client)\/([A-Za-z0-9_-]+)$/)
createApp(publicMatch ? PublicClient : App, publicMatch ? { token: publicMatch[1] } : {}).mount('#app')
window.addEventListener('hashchange', () => window.location.reload())
