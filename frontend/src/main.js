import { createApp } from 'vue'
import './forest-sand.css'
import './themes.css'
import './theme.js'
import App from './App.vue'
import PublicClient from './components/PublicClient.vue'
import LegalPage from './components/LegalPage.vue'

const publicMatch = window.location.hash.match(/^#\/(?:service|client)\/([A-Za-z0-9_-]+)$/)
const legalMatch = window.location.hash.match(/^#\/(privacy|terms)\/?$/)
const root = legalMatch ? LegalPage : publicMatch ? PublicClient : App
const props = legalMatch ? { documentType: legalMatch[1] } : publicMatch ? { token: publicMatch[1] } : {}
createApp(root, props).mount('#app')
window.addEventListener('hashchange', () => window.location.reload())
