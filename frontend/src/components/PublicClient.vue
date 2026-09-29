<script setup>
import { onMounted, ref } from 'vue'
import { ShieldCheck } from 'lucide-vue-next'
import { api } from '../api.js'

const props = defineProps({ token: String })
const data = ref(null)
const loading = ref(true)
const error = ref('')
const date = value => value ? new Date(value + 'T12:00:00').toLocaleDateString('pl-PL') : 'Data do ustalenia'
const money = value => new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(Number(value))
async function load() {
  loading.value = true; error.value = ''; data.value = null
  try {
    const response = await fetch(`${api}/public/service`, { headers: { 'X-Client-Token': props.token }, cache: 'no-store', referrerPolicy: 'no-referrer' })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(body.detail || 'Nie udało się pobrać terminów. Spróbuj ponownie.')
    data.value = body
  } catch (cause) { error.value = cause.message }
  finally { loading.value = false }
}
onMounted(() => {
  document.title = 'TMS · Terminarz klienta'
  for (const [name, content] of [['robots', 'noindex, nofollow, noarchive'], ['referrer', 'no-referrer']]) {
    const meta = document.createElement('meta'); meta.name = name; meta.content = content; document.head.appendChild(meta)
  }
  load()
})
</script>
<template>
  <main class="public-client-page">
    <header class="public-client-header"><div class="brand"><ShieldCheck /><span>TMS</span></div><span>Terminarz klienta</span></header>
    <p v-if="loading" class="empty" role="status">Ładowanie terminów…</p>
    <section v-else-if="error" class="public-section"><h1>Nie można otworzyć terminarza</h1><p class="error" role="alert">{{ error }}</p><button class="primary" @click="load">Spróbuj ponownie</button></section>
    <template v-else-if="data">
      <div class="public-welcome"><p class="eyebrow">TWÓJ HARMONOGRAM</p><h1>{{ data.client.name }}</h1><p>Wszystkie Twoje terminy · {{ data.deadlines.length }}</p></div>
      <section class="public-section public-appointments" aria-labelledby="appointments-title">
        <h2 id="appointments-title">Wszystkie terminy</h2>
        <ul v-if="data.deadlines.length" class="public-appointments-list">
          <li v-for="event in data.deadlines" :key="event.id" class="agenda-event">
            <div><strong>{{ event.title }}</strong><small>{{ date(event.due_date) }}<template v-if="event.scheduled_time"> · {{ event.scheduled_time }}</template></small><small>{{ event.document_id ? 'Dokument' : event.client_service_id ? 'Usługa' : 'Termin własny' }}</small><p v-if="event.cost != null">Koszt: {{ money(event.cost) }}</p><p v-if="event.notes" class="service-description">{{ event.notes }}</p></div>
            <span class="tag">{{ event.status }}</span>
          </li>
        </ul>
        <p v-else class="empty">Brak zapisanych terminów.</p>
      </section>
    </template>
  </main>
</template>
