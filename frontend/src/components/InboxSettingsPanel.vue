<script setup>
import { onMounted, ref } from 'vue'
const props = defineProps({ request: Function })
const form = ref(null), password = ref(''), busy = ref(false), error = ref(''), notice = ref('')
onMounted(async () => { try { form.value = await props.request('/settings/inbox') } catch (cause) { error.value = cause.message } })
async function save() {
  busy.value = true; error.value = ''; notice.value = ''
  try {
    await props.request('/settings/inbox', { method: 'PUT', body: JSON.stringify({ ...form.value, password: password.value || null }) })
    password.value = ''; form.value = await props.request('/settings/inbox'); notice.value = 'Zapisano. Przejdź do Bufora i kliknij „Odbierz pocztę”.'
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
async function startNow() {
  busy.value = true; error.value = ''; notice.value = ''
  try {
    const result = await props.request('/settings/inbox/start-now', { method: 'POST' })
    form.value.sync_from = result.sync_from
    notice.value = 'Ustawiono odbiór tylko nowych wiadomości. Przejdź do Bufora i używaj „Odbierz pocztę”.'
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
</script>
<template>
  <p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
  <form v-if="form" class="entry-form mail-settings-form" @submit.prevent="save">
    <h2>Poczta przychodząca IMAP</h2><p>Wspólna skrzynka dla administratorów i pracowników. Odbiór z folderu INBOX przez szyfrowane połączenie SSL/TLS. Wiadomości pozostają na serwerze pocztowym.</p>
    <fieldset :disabled="busy"><div class="grid">
      <label>Serwer IMAP<input v-model="form.host" required maxlength="255" placeholder="speed.home.pl" /></label>
      <label>Port SSL/TLS<input v-model.number="form.port" type="number" min="1" max="65535" required /></label>
      <label class="mail-field-row">Adres skrzynki / login IMAP<input v-model="form.username" required maxlength="255" autocomplete="off" /><small>Konto, do którego aplikacja loguje się po wiadomości.</small></label>
      <label class="mail-checkbox-row"><input v-model="form.use_smtp_password" type="checkbox" />Użyj hasła zapisanego w ustawieniach SMTP</label>
      <label v-if="!form.use_smtp_password">Hasło IMAP<input v-model="password" type="password" autocomplete="new-password" :required="!form.password_set" /><small>{{ form.password_set ? 'Pozostaw puste, aby zachować zapisane hasło.' : 'Podaj hasło skrzynki.' }}</small></label>
      <label class="mail-field-row">Odbieraj wiadomości tylko od<input v-model="form.sender_filter" type="email" maxlength="255" placeholder="nadawca@firma.pl" /><small>Puste = wszyscy nadawcy. Filtr dotyczy kolejnego odbioru; zapisane wiadomości pozostają w buforze.</small></label>
      <label class="mail-field-row">Prefiks nazw załączników<input v-model="form.attachment_prefix" maxlength="100" placeholder="np. FV_" /><small>Do dokumentów można dodać tylko pliki zaczynające się od tego prefiksu, np. FV_123.pdf. Wielkość liter nie ma znaczenia. Puste = wszystkie pliki.</small></label>
    </div></fieldset>
    <p>Pobieranie odbywa się po kliknięciu „Odbierz pocztę” w Buforze, partiami do 50 wiadomości. Limit wiadomości wraz z załącznikami: 20 MB.</p>
    <button class="primary" :disabled="busy">{{ busy ? 'Zapisywanie…' : 'Zapisz ustawienia IMAP' }}</button>
    <section class="inbox-start">
      <h3>Tylko nowe wiadomości</h3>
      <p>Najpierw zapisz ustawienia IMAP. Ten przycisk zapamięta aktualny stan zapisanej skrzynki bez pobierania treści starych wiadomości. Następny odbiór pobierze tylko wiadomości, które przyjdą później.</p>
      <p v-if="form.sync_from">Ustawiono odbiór od: <strong>{{ new Date(form.sync_from).toLocaleString('pl-PL') }}</strong>. Ponowne kliknięcie przesunie początek odbioru na teraz.</p>
      <p>Wiadomości już zapisane w Buforze pozostaną na liście.</p>
      <button type="button" class="primary" :disabled="busy || !form.configured" @click="startNow">Odbieraj tylko od teraz</button>
    </section>
  </form>
</template>
<style scoped>
.inbox-start{display:grid;gap:12px;margin-top:24px;padding-top:20px;border-top:1px solid var(--line)}
.inbox-start h3{margin:0}.inbox-start button{justify-self:start}
</style>
