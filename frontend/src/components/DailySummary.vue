<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Sparkles, RefreshCw, ArrowUpRight } from 'lucide-vue-next'
const props = defineProps({ request: Function, clients: Array })
defineEmits(['event', 'today'])
const summary = ref(null)
const loading = ref(false)
const error = ref('')
let alive = true
async function refresh() {
  if (loading.value) return
  loading.value = true; error.value = ''
  try {
    const result = await props.request('/dashboard/today-summary', { method: 'POST' })
    if (alive) summary.value = result
  } catch (cause) { if (alive) error.value = cause.message }
  finally { if (alive) loading.value = false }
}
onMounted(refresh)
onBeforeUnmount(() => { alive = false })
</script>
<template>
  <section class="daily-summary" :aria-busy="loading" aria-labelledby="daily-summary-title">
    <div class="summary-heading"><div class="summary-title"><Sparkles :size="21" aria-hidden="true" /><h2 id="daily-summary-title">Twój dzień w skrócie</h2></div><button type="button" class="text-button" :disabled="loading" aria-label="Odśwież podsumowanie dnia" @click="refresh"><RefreshCw :size="15" :class="{ spinning: loading }" />Odśwież</button></div>
    <p v-if="loading && !summary" class="summary-hint" role="status">Przygotowuję podsumowanie dnia…</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-if="summary">
      <div class="summary-meta"><span>{{ summary.source === 'ai' ? 'Podsumowanie AI' : 'Zestawienie bez AI' }}</span><time :datetime="summary.date">{{ new Date(summary.date + 'T12:00:00').toLocaleDateString('pl-PL', { day: 'numeric', month: 'long' }) }}</time></div>
      <p class="summary-text" aria-live="polite">{{ summary.text }}</p>
      <div class="summary-stats"><span><strong>{{ summary.stats.today }}</strong> na dziś</span><span :class="{ overdue: summary.stats.overdue > 0 }"><strong>{{ summary.stats.overdue }}</strong> zaległych</span><span><strong>{{ summary.stats.tomorrow }}</strong> na jutro</span><span><strong>{{ summary.stats.active_services }}</strong> usług w trakcie</span></div>
      <div v-for="group in [{ title: 'Do sprawdzenia', items: summary.overdue_events }, { title: 'Dzisiaj', items: summary.today_events }]" :key="group.title" class="summary-agenda">
        <template v-if="group.items.length"><h3>{{ group.title }}</h3><button v-for="item in group.items" :key="item.id" type="button" class="summary-event" @click="$emit('event', item)"><span><strong>{{ item.title }}</strong><small>{{ clients.find(client => client.id === item.company_id)?.name || 'Bez klienta' }} · {{ item.due_date }}<template v-if="item.scheduled_time"> · {{ item.scheduled_time }}</template></small></span><ArrowUpRight :size="16" aria-hidden="true" /></button></template>
      </div>
      <p v-if="summary.notice" class="summary-hint" role="status">{{ summary.notice }}</p>
      <p v-if="!summary.ai_configured" class="summary-hint">Wersja próbna: zestawienie działa już teraz. Podsumowanie AI włączysz kluczem OPENAI_API_KEY w backend/.env.</p>
      <button type="button" class="text-button" @click="$emit('today')">Zobacz wszystkie sprawy na dziś <ArrowUpRight :size="15" /></button>
    </template>
  </section>
</template>
<style scoped>
.daily-summary { border: 1px solid var(--line); border-radius: 18px; padding: 24px; margin-bottom: 36px; background: var(--theme-surface, #fffefb); color: var(--theme-text, #233b34); }
.summary-heading, .summary-title, .summary-meta { display: flex; align-items: center; gap: 10px; }
.summary-heading { justify-content: space-between; flex-wrap: wrap; }
.summary-title svg { color: var(--forest); }
.summary-title h2 { margin: 0; font-size: 19px; }
.summary-meta { justify-content: space-between; font-size: 11px; color: var(--muted); margin-top: 14px; }
.summary-text { font-size: 14px; line-height: 1.8; white-space: pre-line; margin: 16px 0; }
.summary-stats { display: flex; flex-wrap: wrap; gap: 8px; }
.summary-stats span { display: inline-flex; gap: 6px; align-items: baseline; padding: 8px 10px; border-radius: 9px; background: var(--theme-soft, #f1f4ed); font-size: 12px; }
.summary-stats strong { font-size: 17px; }
.summary-stats .overdue { color: var(--theme-danger, #993e32); background: var(--theme-danger-bg, #fff0eb); }
.summary-agenda h3 { font-size: 12px; color: var(--muted); margin: 18px 0 6px; }
.summary-event { display: flex; align-items: center; justify-content: space-between; gap: 12px; width: 100%; background: transparent; color: inherit; text-align: left; padding: 9px 0; border-bottom: 1px solid var(--line); }
.summary-event:hover { color: var(--forest); }
.summary-event strong { font-size: 13px; font-weight: 550; }
.summary-event small { display: block; margin-top: 5px; color: var(--muted); font-size: 11px; }
.summary-event span { overflow-wrap: anywhere; min-width: 0; }
.summary-event svg { flex-shrink: 0; }
.summary-hint { color: var(--muted); font-size: 12px; line-height: 1.6; }
.daily-summary > .text-button { margin-top: 12px; }
.spinning { animation: summary-spin 1.5s linear infinite; }
@keyframes summary-spin { to { transform: rotate(360deg); } }
@media (max-width: 600px) { .daily-summary { padding: 18px; } }
@media (prefers-reduced-motion: reduce) { .spinning { animation: none; } }
</style>
