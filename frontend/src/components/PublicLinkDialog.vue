<script setup>
import { computed, ref } from 'vue'
import { X } from 'lucide-vue-next'
const props = defineProps({ request: Function })
const client = ref(null)
const busy = ref(false)
const error = ref('')
const message = ref('')
const link = ref({ token: null, expires_at: null })
const url = computed(() => link.value.token ? `${window.location.origin}${window.location.pathname}#/service/${link.value.token}` : '')
async function open(item) {
  client.value = item
  link.value = { token: null, expires_at: null }
  await operate('GET')
}
async function operate(method) {
  busy.value = true
  error.value = ''; message.value = ''
  try {
    const result = await props.request(`/client-services/${client.value.id}/public-link`, { method })
    link.value = method === 'DELETE' ? { token: null, expires_at: null } : result
    if (method === 'DELETE') message.value = 'Link został unieważniony.'
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
async function copy() {
  try { await navigator.clipboard.writeText(url.value); message.value = 'Skopiowano link.' }
  catch { message.value = 'Zaznacz link w polu i skopiuj go ręcznie.' }
}
defineExpose({ open })
</script>
<template>
  <div v-if="client" class="modal-backdrop" @click.self="!busy && (client = null)">
    <section class="entry-form modal public-link-dialog" role="dialog" aria-modal="true" aria-labelledby="public-link-title">
      <div class="modal-title"><h2 id="public-link-title">Link usługi: {{ client.name }}</h2><button class="icon-button" aria-label="Zamknij" :disabled="busy" @click="client = null"><X :size="18" /></button></div>
      <p class="form-hint">Osoba z linkiem zobaczy terminarz przypisanego klienta: wszystkie jego terminy z usług i dokumentów oraz wpisy własne. Link jest ważny przez 30 dni.</p>
      <p v-if="busy" class="form-hint">Ładowanie…</p>
      <template v-if="url">
        <label>Link do skopiowania do SMS-a<input :value="url" readonly @focus="$event.target.select()" /></label>
        <p class="form-hint">Ważny do: {{ new Date(link.expires_at).toLocaleString('pl-PL') }}</p>
        <div class="public-link-actions"><button class="primary" :disabled="busy" @click="copy">Kopiuj link</button><a class="text-button" :href="url" target="_blank" rel="noopener noreferrer">Otwórz podgląd</a></div>
        <div class="public-link-actions"><button class="text-button" :disabled="busy" @click="operate('POST')">Wygeneruj nowy link</button><button class="text-button" :disabled="busy" @click="operate('DELETE')">Unieważnij link</button></div>
      </template>
      <button v-else-if="!busy && !error" class="primary" @click="operate('POST')">Utwórz link usługi</button>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button v-if="error && !busy" class="text-button" @click="operate('GET')">Ponów</button>
      <p v-if="message" class="form-hint" role="status">{{ message }}</p>
    </section>
  </div>
</template>
