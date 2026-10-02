<script setup>
import { onMounted, ref } from 'vue'
import InboxSettingsPanel from './InboxSettingsPanel.vue'
const props = defineProps({ request: Function })
const form = ref(null), password = ref(''), clearPassword = ref(false), busy = ref(false), error = ref(''), notice = ref('')
onMounted(async () => { try { form.value = await props.request('/settings/mail') } catch (cause) { error.value = cause.message } })
async function save() {
  busy.value = true; error.value = ''; notice.value = ''
  try {
    await props.request('/settings/mail', { method: 'PUT', body: JSON.stringify({ ...form.value, password: clearPassword.value ? '' : password.value || null }) })
    password.value = ''; clearPassword.value = false
    form.value = await props.request('/settings/mail'); notice.value = 'Zapisano ustawienia poczty.'
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
</script>
<template>
  <p v-if="error && !form" class="error" role="alert">{{ error }}</p>
  <form v-if="form" class="entry-form mail-settings-form" @submit.prevent="save">
    <h2>Poczta wychodząca SMTP</h2>
    <p>Te ustawienia służą do wysyłania potwierdzeń utworzenia konta z hasłem tymczasowym.</p>
    <fieldset :disabled="busy"><div class="grid">
      <label>Serwer SMTP<input v-model.trim="form.host" required maxlength="255" placeholder="smtp.gmail.com" pattern="[a-zA-Z0-9.\-]+" title="Sama nazwa serwera, np. smtp.gmail.com, bez https:// i numeru portu" /><small>Sam adres serwera, bez https:// i portu.</small></label>
      <label>Port<input v-model.number="form.port" type="number" min="1" max="65535" required /></label>
      <label>Szyfrowanie<select v-model="form.security"><option value="starttls">STARTTLS (zwykle port 587)</option><option value="ssl">TLS (zwykle port 465)</option></select></label>
      <label>Login SMTP<input v-model.trim="form.username" maxlength="255" autocomplete="off" /></label>
      <label>Hasło SMTP<input v-model="password" type="password" autocomplete="new-password" :disabled="clearPassword" /><small>{{ form.password_set ? 'Hasło zapisane. Pozostaw puste, aby je zachować.' : 'Hasło nie jest ustawione.' }}</small></label>
      <label class="mail-checkbox-row"><input v-model="clearPassword" type="checkbox" />Usuń zapisane hasło SMTP</label>
      <label class="mail-field-row">E-mail nadawcy<input v-model.trim="form.sender" type="email" maxlength="255" required /></label>
      <label class="mail-field-row">Adres panelu<input v-model.trim="form.public_url" type="url" maxlength="2048" pattern="https://.+" title="Adres aplikacji zaczynający się od https://" placeholder="https://katia.mdriver.pl" /><small>Link w wiadomości do użytkownika, np. https://katia.mdriver.pl. Wymagany HTTPS; pole można zostawić puste.</small></label>
    </div></fieldset>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="notice" role="status">{{ notice }}</p>
    <button type="submit" class="primary" :disabled="busy">{{ busy ? 'Zapisywanie…' : 'Zapisz SMTP' }}</button>
  </form>
  <section class="incoming-settings"><InboxSettingsPanel :request="request" /></section>
</template>
<style scoped>
.incoming-settings{margin-top:32px;padding-top:24px;border-top:1px solid var(--line)}
</style>
