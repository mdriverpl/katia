<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { CalendarDays, X } from 'lucide-vue-next'
import DailySummary from './DailySummary.vue'
import { statusInfo } from '../status.js'
const props = defineProps({ request: Function, clients: Array, deadlines: Array, documents: Array, busy: Boolean })
const emit = defineEmits(['event', 'today', 'calendar'])
const opened = ref(false)
const root = ref(null)
const trigger = ref(null)
const closeButton = ref(null)
const today = ref(warsawDay())
function warsawDay() { return new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Warsaw', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()) }
const closedDocuments = computed(() => new Set(props.documents.filter(item => ['done', 'neutral'].includes(statusInfo(item.status).tone)).map(item => item.id)))
const pending = computed(() => props.deadlines.filter(item => !closedDocuments.value.has(item.document_id) && !['done', 'neutral'].includes(statusInfo(item.status).tone)))
const count = computed(() => pending.value.filter(item => item.due_date === today.value).length)
const overdue = computed(() => pending.value.filter(item => item.due_date && item.due_date < today.value).length)
const previewMood = ref('wide-eyes')
const wideEyes = computed(() => previewMood.value === 'wide-eyes' || count.value === 0)
const overwhelmed = computed(() => previewMood.value ? previewMood.value === 'overwhelmed' : count.value + overdue.value >= 10)
const headline = computed(() => {
  if (props.busy) return 'Sprawdzam Twój dzień…'
  if (!count.value) return 'Dziś bez otwartych terminów'
  const n = count.value
  const noun = n === 1 ? 'termin' : n % 10 >= 2 && n % 10 <= 4 && !(n % 100 >= 12 && n % 100 <= 14) ? 'terminy' : 'terminów'
  return `Masz dziś ${n} ${noun}`
})
async function toggle() {
  opened.value = !opened.value
  if (opened.value) { await nextTick(); closeButton.value?.focus() }
}
function close(restore = false) { opened.value = false; if (restore) trigger.value?.focus() }
function outside(event) { if (root.value && !root.value.contains(event.target)) close() }
let timer
onMounted(() => { document.addEventListener('pointerdown', outside); timer = setInterval(() => { today.value = warsawDay() }, 60000) })
onBeforeUnmount(() => { document.removeEventListener('pointerdown', outside); clearInterval(timer) })
function openEvent(item) { close(); emit('event', item) }
function openToday() { close(); emit('today') }
function openCalendar() { close(); emit('calendar', today.value) }
</script>
<template>
  <div ref="root" class="header-assistant" @keydown.esc.stop="close(true)">
    <div class="assistant-overview">
    <button ref="trigger" type="button" class="assistant-trigger" aria-label="Otwórz podsumowanie dnia" :aria-expanded="opened" aria-controls="header-assistant-panel" @click="toggle">
      <span class="assistant-avatar" :class="{ 'is-overwhelmed': overwhelmed && !wideEyes, 'is-relaxed': !overwhelmed && !wideEyes, 'is-startled': wideEyes }" aria-hidden="true">
        <svg viewBox="0 0 80 80" fill="none" focusable="false">
          <g class="assistant-character" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="17" y="16" width="42" height="46" rx="18" />
            <path :d="overwhelmed || wideEyes ? 'M29 62v9h-7m25-9v9h7' : 'M29 62l6 9h-8m20-9-8 9h8'" />
            <path v-if="!wideEyes" d="M17 40C7 40 6 50 11 54m0 0-5-1m5 1-1 5" />
            <template v-if="wideEyes">
              <path d="M17 40C5 34 8 17 10 9m0 0-5-4m5 4V2m0 7 5-5M59 40c12-6 9-23 7-31m0 0 5-4m-5 4V2m0 7-5-5" />
              <g class="assistant-eyes"><ellipse cx="29" cy="34" rx="7" ry="9" /><ellipse cx="47" cy="34" rx="7" ry="9" /><circle cx="29" cy="35" r="1.5" fill="currentColor" /><circle cx="47" cy="35" r="1.5" fill="currentColor" /></g>
              <path d="m24 21 8-2m12 0 8 2" />
              <ellipse cx="38" cy="51" rx="4" ry="5" />
            </template>
            <template v-else-if="overwhelmed">
              <path d="M59 43c10 0 9 9 8 12m0 0 4-2m-4 2 2 4" />
              <g class="assistant-eyes">
                <ellipse cx="30" cy="35" rx="3" ry="4" /><ellipse cx="46" cy="35" rx="3" ry="4" />
              </g>
              <path d="m25 27 8-3m10 0 8 3M31 50q7-8 14 0" />
              <path class="assistant-sweat" d="M63 16s-4 5-4 8a4 4 0 0 0 8 0c0-3-4-8-4-8Z" stroke-width="1.5" />
              <path class="assistant-sweat second-drop" d="M12 20s-3 4-3 6a3 3 0 0 0 6 0c0-2-3-6-3-6Z" stroke-width="1.5" />
            </template>
            <template v-else>
              <path d="M59 43q12 18 0 19l-7-7" />
              <g class="assistant-eyes">
                <path d="M26 35q4-5 8 0m8 0q4-5 8 0" />
              </g>
              <path d="M31 45q7 8 14 0" />
              <path d="M71 47h2a5 5 0 0 1 0 10h-2" stroke-width="2.5" />
              <path class="assistant-cup" d="M53 43h18v14a6 6 0 0 1-6 6h-6a6 6 0 0 1-6-6Z" stroke-width="2.5" />
              <path d="M57 47h10m-16 7h5" stroke-width="2" />
              <path class="assistant-steam" d="M58 38c-4-4 4-6 0-11m8 11c-4-4 4-6 0-11" stroke-width="1.8" />
            </template>
          </g>
        </svg>
      </span>
    </button>
    <span class="assistant-copy"><button type="button" class="assistant-calendar" :disabled="busy" aria-label="Otwórz kalendarz na dzisiaj" @click="openCalendar"><CalendarDays :size="17" aria-hidden="true" /><strong>{{ headline }}</strong></button><small>{{ overdue ? `Zaległe: ${overdue} · sprawdź podsumowanie` : 'Twój asystent dnia' }}</small></span>
    </div>
    <button v-if="previewMood" type="button" class="assistant-preview-reset" @click="previewMood = null">Podgląd wielkich oczu · wróć do auto</button>
    <div v-if="opened" id="header-assistant-panel" class="assistant-popover" role="region" aria-label="Asystent — podsumowanie dnia">
      <div class="assistant-toolbar"><span>Asystent Space &amp; Flow</span><button ref="closeButton" type="button" class="icon-button" aria-label="Zamknij podsumowanie" @click="close(true)"><X :size="17" /></button></div>
      <DailySummary :request="request" :clients="clients" @event="openEvent" @today="openToday" />
    </div>
  </div>
</template>
<style scoped>
.header-assistant { position: relative; }
.assistant-overview { display: flex; align-items: center; gap: 4px; }
.assistant-calendar { display: inline-flex; align-items: center; gap: 7px; padding: 4px 0; background: transparent; color: inherit; text-align: left; }
.assistant-calendar svg { flex-shrink: 0; color: var(--forest); }
.assistant-calendar:hover { color: var(--forest); }
.assistant-calendar:focus-visible { outline: 2px solid var(--forest); outline-offset: 3px; }
.assistant-preview-reset { display: block; margin: 0 auto; padding: 3px 6px; background: transparent; color: var(--muted); font-size: 10px; text-decoration: underline; text-underline-offset: 3px; }
.assistant-trigger { display: flex; align-items: center; gap: 11px; padding: 7px 10px; border-radius: 14px; color: var(--theme-text, #233b34); background: transparent; text-align: left; }
.assistant-trigger:hover, .assistant-trigger[aria-expanded='true'] { background: var(--theme-soft, #eef2e8); }
.assistant-trigger:focus-visible { outline: 2px solid var(--forest); outline-offset: 3px; }
.assistant-avatar { display: grid; place-items: center; width: 72px; height: 72px; flex-shrink: 0; color: var(--forest); }
.assistant-avatar > svg { display: block; width: 100%; height: 100%; }
.assistant-character { animation: assistant-float 5s ease-in-out infinite; }
.assistant-eyes { transform-box: fill-box; transform-origin: center; animation: assistant-blink 6s ease-in-out infinite; }
.is-relaxed .assistant-character { transform-origin: 38px 62px; animation: assistant-relax 6s ease-in-out infinite; }
.assistant-sweat { animation: assistant-drip 2s ease-in infinite; }
.second-drop { animation-delay: -1s; }
.assistant-steam { animation: assistant-steam-rise 3s ease-out infinite; }
.assistant-cup { fill: var(--theme-surface, #fffefb); }
.assistant-copy { display: grid; gap: 4px; }
.assistant-copy strong { font-size: 12px; font-weight: 600; }
.assistant-copy small { color: var(--muted); font-size: 10px; }
.assistant-popover { position: absolute; right: 0; top: calc(100% + 12px); width: min(560px, calc(100vw - 32px)); max-height: min(720px, 75vh); overflow-y: auto; z-index: 30; border: 1px solid var(--line); border-radius: 18px; background: var(--theme-surface, #fffefb); box-shadow: 0 16px 55px #102e2826; }
.assistant-toolbar { display: flex; justify-content: space-between; align-items: center; padding: 12px 18px 0; font-size: 11px; color: var(--muted); }
.assistant-popover :deep(.daily-summary) { border: 0; margin: 0; padding: 18px; }
@keyframes assistant-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-2px); } }
@keyframes assistant-blink { 0%, 44%, 48%, 100% { transform: scaleY(1); } 46% { transform: scaleY(.1); } }
@keyframes assistant-relax { 0%, 100% { transform: rotate(-4deg); } 50% { transform: rotate(-1deg) translateY(-1px); } }
@keyframes assistant-drip { 0% { opacity: 0; transform: translateY(-3px); } 20% { opacity: 1; } 100% { opacity: 0; transform: translateY(14px); } }
@keyframes assistant-steam-rise { 0% { opacity: .2; transform: translateY(2px); } 30% { opacity: .8; } 100% { opacity: 0; transform: translateY(-8px); } }
@media (max-width: 820px) { .assistant-popover { position: fixed; top: 90px; right: 16px; max-height: calc(100dvh - 110px); } }
@media (prefers-reduced-motion: reduce) { .assistant-character, .is-relaxed .assistant-character, .assistant-eyes, .assistant-sweat, .assistant-steam { animation: none; } .assistant-steam { opacity: .4; } }
</style>
