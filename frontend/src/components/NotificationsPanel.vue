<script setup>
import { computed, onMounted, ref } from 'vue'
const props = defineProps({ request: Function, clients: Array, services: Array })
const settings = ref(null)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const serviceId = ref('')
const requestId = ref(null)
const sent = ref(false)
const methods = { whatsapp: 'WhatsApp Business', smsapi: 'SMS (SMSAPI)' }
const defaultMethod = ref('whatsapp')
const automatic = ref(false)
const activeProvider = computed(() => settings.value?.providers[settings.value.default_method])
const service = computed(() => props.services.find(item => item.id === serviceId.value))
const recipient = computed(() => props.clients.find(item => item.id === service.value?.company_id))
const statuses = { accepted: 'Przyjęta przez operatora', pending: 'Wysyłka rozpoczęta — sprawdź u operatora', unconfirmed: 'Wysyłka niepotwierdzona — sprawdź u operatora' }
async function load() {
  settings.value = await props.request('/notifications/settings')
  defaultMethod.value = settings.value.default_method
  automatic.value = settings.value.automatic
}
async function saveSettings() {
  busy.value = true; error.value = ''; notice.value = ''
  try {
    await props.request('/notifications/settings', { method: 'PUT', body: JSON.stringify({ default_method: defaultMethod.value, automatic: automatic.value }) })
    await load()
    notice.value = 'Zapisano ustawienia powiadomień.'
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
onMounted(async () => { try { await load() } catch (cause) { error.value = cause.message } })
async function subscribe(client) {
  busy.value = true; error.value = ''; notice.value = ''
  try {
    const enabled = settings.value.subscribed_clients.includes(client.id)
    await props.request(`/notifications/subscriptions/${client.id}`, { method: enabled ? 'DELETE' : 'PUT' })
    await load()
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
async function send() {
  if (busy.value || !recipient.value) return
  busy.value = true; error.value = ''; notice.value = ''
  try {
    requestId.value ||= crypto.randomUUID()
    const result = await props.request(`/notifications/services/${serviceId.value}/link`, { method: 'POST', body: JSON.stringify({ request_id: requestId.value }) })
    notice.value = `${statuses[result.status]} (${methods[result.provider]}).`
    sent.value = true
    if (result.error) error.value = result.error
    await load()
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
</script>
<template>
  <section class="whatsapp-settings">
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="notice" role="status">{{ notice }}</p>
    <p v-if="!settings && !error">Ładowanie konfiguracji…</p>
    <template v-if="settings">
      <form class="entry-form service-template-page deadline-type-form" @submit.prevent="saveSettings">
        <h2>Domyślna metoda wysyłki</h2>
        <label>Linki i przypomnienia<select v-model="defaultMethod" :disabled="busy"><option v-for="(label, key) in methods" :key="key" :value="key">{{ label }}</option></select></label>
        <label class="whatsapp-toggle"><input v-model="automatic" type="checkbox" :disabled="busy" />Automatyczne przypomnienia dzień przed terminem</label>
        <p>Wysyłka od godziny 09:00 czasu polskiego. Wybrana metoda będzie używana dla wszystkich włączonych klientów.</p>
        <button class="primary" :disabled="busy">Zapisz ustawienia</button>
        <p>Obecnie: <strong>{{ methods[settings.default_method] }}</strong>. Przypomnienia: <strong>{{ settings.automatic && activeProvider?.ready ? 'włączone' : 'wyłączone lub oczekujące na konfigurację' }}</strong>.</p>
      </form>
      <section v-for="(provider, key) in settings.providers" :key="key" class="service-template-page">
        <h2>{{ methods[key] }}</h2>
        <p>{{ provider.ready ? 'Konfiguracja uzupełniona. Połączenie zostanie sprawdzone przy wysyłce.' : 'Oczekuje na konfigurację.' }}</p>
        <details :open="!provider.ready"><summary>Konfiguracja integracji</summary>
          <p v-if="key === 'whatsapp'">Skonfiguruj konto Meta i zatwierdź szablony. Instrukcja: docs/whatsapp.md.</p>
          <p v-else>W panelu SMSAPI.pl utwórz token OAuth i skonfiguruj pole nadawcy. Wpisz SMSAPI_ACCESS_TOKEN oraz SMSAPI_SENDER w backend/.env. Instrukcja: docs/smsapi.md.</p>
          <p>Ustaw PUBLIC_APP_URL na publiczny adres HTTPS aplikacji. Po zmianie backend/.env uruchom ponownie backend.</p>
          <p v-if="provider.missing.length">Brakujące ustawienia: {{ provider.missing.join(', ') }}</p>
          <p v-for="issue in provider.issues" :key="issue" class="error">{{ issue }}</p>
        </details>
      </section>
      <form class="entry-form service-template-page" @submit.prevent="send">
        <h2>Wyślij link do terminarza</h2>
        <label>Usługa klienta<select v-model="serviceId" :disabled="busy" required @change="requestId = null; sent = false; notice = ''; error = ''"><option value="" disabled>Wybierz usługę</option><option v-for="item in services" :key="item.id" :value="item.id">{{ clients.find(client => client.id === item.company_id)?.name }} — {{ item.name }}</option></select></label>
        <p v-if="recipient">Odbiorca: <strong>{{ recipient.name }}</strong> · {{ recipient.phone || 'Brak telefonu' }}</p>
        <p class="form-hint">Wyślemy nazwę klienta i jego aktywny link przez {{ methods[settings.default_method] }}. Link utworzysz w Usługi → Link usługi.</p>
        <p v-if="settings.default_method === 'smsapi'" class="form-hint">SMS z długim linkiem lub polskimi znakami może być rozliczony jako kilka części.</p>
        <button class="primary" :disabled="busy || !activeProvider?.ready || !recipient?.phone || sent">{{ busy ? 'Proszę czekać…' : `Wyślij przez ${methods[settings.default_method]}` }}</button>
        <p class="form-hint">Przyjęcie wiadomości przez operatora nie oznacza jeszcze doręczenia.</p>
      </form>
      <section class="data-list deadline-types-list">
        <h2>Automatyczne przypomnienia</h2>
        <p>Włączaj dla klientów, którzy zgodzili się na wiadomości wybraną metodą. Uwzględniamy terminy widoczne w kalendarzu klienta z usług, dokumentów i terminarza. Backend musi być uruchomiony.</p>
        <div class="whatsapp-table"><table><thead><tr><th>Klient</th><th>Telefon</th><th>Przypomnienia</th></tr></thead><tbody><tr v-for="client in clients" :key="client.id"><td>{{ client.name }}</td><td>{{ client.phone || '—' }}</td><td><label class="whatsapp-toggle"><input type="checkbox" :checked="settings.subscribed_clients.includes(client.id)" :disabled="busy" :aria-label="'Przypomnienia: ' + client.name" @change="subscribe(client)" />{{ settings.subscribed_clients.includes(client.id) ? 'Włączone' : 'Wyłączone' }}</label></td></tr></tbody></table></div>
      </section>
      <section class="data-list"><h2>Ostatnie wysyłki</h2><p v-if="!settings.history.length">Nie wysłano jeszcze wiadomości.</p><div v-else class="whatsapp-table"><table><thead><tr><th>Data</th><th>Klient</th><th>Wiadomość</th><th>Metoda</th><th>Status</th></tr></thead><tbody><tr v-for="item in settings.history" :key="item.id"><td>{{ new Date(item.created_at.endsWith('Z') || /[+-]\d\d:\d\d$/.test(item.created_at) ? item.created_at : item.created_at + 'Z').toLocaleString('pl-PL') }}</td><td>{{ clients.find(client => client.id === item.company_id)?.name || '—' }}</td><td>{{ item.title }}</td><td>{{ methods[item.provider] }}</td><td>{{ statuses[item.status] }}<small v-if="item.error">{{ item.error }}</small></td></tr></tbody></table></div></section>
    </template>
  </section>
</template>
<style scoped>
.whatsapp-settings { display: grid; gap: 20px; }
.whatsapp-settings h2 { font-size: 18px; margin: 0 0 14px; }
.whatsapp-settings p, .whatsapp-settings li { line-height: 1.6; }
.whatsapp-settings .data-list { padding: 20px; }
.whatsapp-table { overflow-x: auto; }
.whatsapp-settings small { display: block; max-width: 300px; margin-top: 6px; }
.whatsapp-toggle { display: flex; gap: 8px; align-items: center; }
.whatsapp-settings select { width: 100%; }
</style>
