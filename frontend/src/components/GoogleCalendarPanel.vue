<script setup>
import { computed, onMounted, ref } from 'vue'
const props = defineProps({ request: Function })
const form = ref(null), secret = ref(''), busy = ref(false), error = ref(''), notice = ref('')
const callback = computed(() => (form.value?.public_url || window.location.origin).replace(/\/$/, '') + '/api/integrations/google-calendar/callback')
const calendarUrl = computed(() => 'https://calendar.google.com/calendar/u/0/r?cid=' + encodeURIComponent(form.value?.calendar_id || ''))
async function load() {
  form.value = await props.request('/integrations/google-calendar')
  if (!form.value.public_url) form.value.public_url = window.location.origin
}
async function run(action) {
  if (busy.value) return
  busy.value = true; error.value = ''; notice.value = ''
  try { await action() } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
async function save() {
  await run(async () => {
    await props.request('/integrations/google-calendar', { method: 'PUT', body: JSON.stringify({ client_id: form.value.client_id.trim(), client_secret: secret.value || null, public_url: form.value.public_url, automatic: form.value.automatic }) })
    secret.value = ''; await load(); notice.value = 'Zapisano ustawienia Kalendarza Google.'
  })
}
function connect() {
  return run(async () => {
    const result = await props.request('/integrations/google-calendar/connect', { method: 'POST' })
    window.location.assign(result.url)
  })
}
function sync() {
  return run(async () => {
    try {
      const result = await props.request('/integrations/google-calendar/sync', { method: 'POST' })
      notice.value = `Synchronizacja zakończona. Dodano: ${result.created}, zaktualizowano: ${result.updated}, usunięto: ${result.deleted}, bez zmian: ${result.unchanged}.`
    } finally { await load() }
  })
}
function disconnect() {
  if (!confirm('Rozłączyć Kalendarz Google? Synchronizacja zostanie zatrzymana. Dotychczasowe wydarzenia pozostaną w Google.')) return
  return run(async () => {
    const result = await props.request('/integrations/google-calendar/connection', { method: 'DELETE' })
    await load(); notice.value = result.warning || 'Rozłączono Kalendarz Google.'
  })
}
onMounted(() => run(load))
</script>

<template>
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <p v-if="notice" role="status">{{ notice }}</p>
  <template v-if="form">
    <section class="entry-form">
      <h2>Terminy w Kalendarzu Google</h2>
      <p>Połącz konto, aby wysyłać terminy do osobnego kalendarza „Space &amp; Flow”. Eksport obejmuje terminy widoczne w Terminarzu: własne, dokumentów i usług.</p>
      <p>Google otrzyma tytuł, imię i nazwisko klienta, datę, godzinę, status i adres terminu. Wydarzenia bez konkretnej godziny będą całodniowe; wydarzenia z godziną będą miały długość jednej godziny.</p>
      <p>Zmieniaj terminy w tej aplikacji. Synchronizacja aktualizuje wydarzenia i usuwa te, których nie ma już w Terminarzu. Zmiany z Google nie wracają do aplikacji.</p>
      <p><strong>{{ form.connected ? 'Kalendarz połączony' : 'Kalendarz nie jest połączony' }}</strong></p>
      <p v-if="form.last_synced_at">Ostatnia synchronizacja: {{ new Date(form.last_synced_at).toLocaleString('pl-PL') }}</p>
      <p v-if="form.last_error" class="error" role="alert">{{ form.last_error }}</p>
      <div class="service-page-actions">
        <button v-if="form.client_secret_set" class="primary" :disabled="busy" @click="connect">{{ form.connected ? 'Ponownie autoryzuj Google' : 'Połącz z Google' }}</button>
        <button v-if="form.connected" class="text-button" :disabled="busy" @click="sync">{{ busy ? 'Przetwarzanie…' : 'Synchronizuj teraz' }}</button>
        <a v-if="form.connected" :href="calendarUrl" target="_blank" rel="noopener noreferrer">Otwórz kalendarz</a>
        <button v-if="form.connected" class="text-button" :disabled="busy" @click="disconnect">Rozłącz</button>
      </div>
    </section>
    <form class="entry-form" @submit.prevent="save">
      <h2>Konfiguracja połączenia</h2>
      <details :open="!form.client_secret_set">
        <summary>Jak przygotować dostęp Google</summary>
        <ol>
          <li>W <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer">Google Cloud Console</a> utwórz projekt i włącz Google Calendar API.</li>
          <li>Skonfiguruj ekran zgody OAuth. Jeśli aplikacja działa w trybie testowym, dodaj swoje konto do użytkowników testowych.</li>
          <li>Utwórz klienta OAuth typu „Web application”. W dozwolonych adresach przekierowania wpisz dokładnie adres pokazany poniżej.</li>
          <li>Wklej Client ID i Client Secret, zapisz ustawienia i kliknij „Połącz z Google”.</li>
        </ol>
        <p>Dostęp obejmuje wyłącznie kalendarze utworzone przez tę aplikację. Szczegóły konfiguracji: <a href="https://developers.google.com/identity/protocols/oauth2/web-server" target="_blank" rel="noopener noreferrer">dokumentacja Google OAuth</a>.</p>
      </details>
      <fieldset :disabled="busy"><div class="grid">
        <label>Adres panelu<input v-model="form.public_url" type="url" required placeholder="https://panel.example.com" /><small>HTTPS; lokalnie dozwolone jest HTTP na localhost.</small></label>
        <label>Adres przekierowania OAuth<input :value="callback" readonly @focus="$event.target.select()" /></label>
        <label>Google Client ID<input v-model="form.client_id" required maxlength="255" :disabled="form.connected" autocomplete="off" /></label>
        <label>Google Client Secret<input v-model="secret" type="password" :required="!form.client_secret_set" autocomplete="new-password" /><small>{{ form.client_secret_set ? 'Sekret zapisany. Puste pole zachowuje dotychczasową wartość.' : 'Wymagany przy pierwszej konfiguracji.' }}</small></label>
        <label><input v-model="form.automatic" type="checkbox" />Automatyczna synchronizacja co 5 minut</label>
      </div></fieldset>
      <button class="primary" :disabled="busy">{{ busy ? 'Przetwarzanie…' : 'Zapisz ustawienia' }}</button>
    </form>
  </template>
</template>
