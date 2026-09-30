import { ref } from 'vue'

export const themes = [
  { id: 'basic', name: 'Podstawowy', icon: '🌿', hint: 'Spokojnie, po naszemu' },
  { id: 'sweet', name: 'Słodki', icon: '🧁', hint: 'Odrobina lukru do pracy' },
  { id: 'dark', name: 'Tajemniczy', icon: '🕵️', hint: 'Tryb tajnego agenta' },
  { id: 'colorful', name: 'Kolorowy', icon: '😜', hint: 'Dobry humor w każdym kolorze' },
]
const valid = value => themes.some(item => item.id === value)
let saved = 'basic'
try { saved = localStorage.getItem('tms_theme') || 'basic' } catch { /* Storage may be unavailable. */ }
export const theme = ref(valid(saved) ? saved : 'basic')
document.documentElement.dataset.theme = theme.value
export function setTheme(value) {
  if (!valid(value)) return
  theme.value = value
  document.documentElement.dataset.theme = value
  try { localStorage.setItem('tms_theme', value) } catch { /* Keep the current session usable. */ }
}
window.addEventListener('storage', event => {
  if (event.key === 'tms_theme') {
    theme.value = valid(event.newValue) ? event.newValue : 'basic'
    document.documentElement.dataset.theme = theme.value
  }
})
