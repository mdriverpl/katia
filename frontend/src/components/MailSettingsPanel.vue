<script setup>
import { onMounted, ref } from 'vue'
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
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <p v-if="notice" role="status">{{ notice }}</p>
  <form v-if="form" class="entry-form" @submit.prevent="save">
    <h2>Poczta wychodząca SMTP</h2>
    <p>Te ustawienia służą do wysyłania potwierdzeń utworzenia konta z hasłem tymczasowym.</p>
    <fieldset :disabled="busy"><div class="grid">
      <label>Serwer SMTP<input v-model="form.host" required maxlength="255" placeholder="smtp.example.com" /></label>
      <label>Port<input v-model.number="form.port" type="number" min="1" max="65535" required /></label>
      <label>Szyfrowanie<select v-model="form.security"><option value="starttls">STARTTLS (zwykle port 587)</option><option value="ssl">TLS (zwykle port 465)</option></select></label>
      <label>Login SMTP<input v-model="form.username" maxlength="255" autocomplete="off" /></label>
      <label>Hasło SMTP<input v-model="password" type="password" autocomplete="new-password" :disabled="clearPassword" /><small>{{ form.password_set ? 'Hasło zapisane. Pozostaw puste, aby je zachować.' : 'Hasło nie jest ustawione.' }}</small></label>
      <label><input v-model="clearPassword" type="checkbox" />Usuń zapisane hasło SMTP</label>
      <label>E-mail nadawcy<input v-model="form.sender" type="email" maxlength="255" required /></label>
      <label>Adres panelu<input v-model="form.public_url" type="url" placeholder="https://panel.example.com" /><small>Link umieszczany w wiadomości do użytkownika.</small></label>
    </div></fieldset>
    <button class="primary" :disabled="busy">{{ busy ? 'Zapisywanie…' : 'Zapisz ustawienia' }}</button>
  </form>
</template>
