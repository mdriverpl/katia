<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
const props = defineProps({ request: Function, clients: Array, types: Array })
const emit = defineEmits(['saved'])
const messages = ref([]), selected = ref(null), busy = ref(false), loading = ref(false)
const error = ref(''), notice = ref(''), offset = ref(0), hasMore = ref(false)
const form = ref({ company_id: '', document_type_id: '', number: '', attachments: [] })
let generation = 0
onBeforeUnmount(() => { generation++ })
function date(value) { return new Date(value).toLocaleString('pl-PL') }
async function load() {
  const result = await props.request(`/inbox?offset=${offset.value}`)
  messages.value = result.items; hasMore.value = result.has_more
}
async function page(direction) {
  busy.value = true; error.value = ''
  const previous = offset.value
  offset.value += direction * 50
  try { await load() } catch (cause) { offset.value = previous; error.value = cause.message }
  finally { busy.value = false }
}
async function open(item) {
  const current = ++generation
  loading.value = true; selected.value = null; error.value = ''; notice.value = ''
  try {
    const result = await props.request(`/inbox/${item.id}`)
    if (current !== generation) return
    selected.value = result
    form.value = { company_id: '', document_type_id: '', number: '', attachments: result.attachments.filter(file => !file.document_id && file.eligible !== false).slice(0, 10).map(file => file.id) }
  } catch (cause) { if (current === generation) error.value = cause.message }
  finally { if (current === generation) loading.value = false }
}
async function sync() {
  busy.value = true; error.value = ''; notice.value = ''
  try {
    const result = await props.request('/inbox/sync', { method: 'POST' })
    offset.value = 0; await load()
    notice.value = `Odebrano ${result.imported} wiadomości.`
    if (result.skipped) notice.value += ` Pominięto ${result.skipped} wiadomości większych niż 20 MB.`
    if (result.filtered) notice.value += ` Pominięto ${result.filtered} wiadomości od innych nadawców.`
    if (result.remaining) notice.value += ` Pozostało ${result.remaining}. Kliknij „Odbierz pocztę” ponownie.`
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
async function download(file) {
  busy.value = true; error.value = ''
  try {
    const blob = await props.request(`/inbox/${selected.value.id}/attachments/${file.id}`, { download: true })
    const url = URL.createObjectURL(blob), link = document.createElement('a')
    link.href = url; link.download = file.name; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
async function save() {
  busy.value = true; error.value = ''; notice.value = ''
  const id = selected.value.id
  try {
    await props.request(`/inbox/${id}/documents`, { method: 'POST', body: JSON.stringify(form.value) })
    // Mark success immediately, even if refreshing the detail fails afterwards.
    for (const file of selected.value.attachments) if (form.value.attachments.includes(file.id)) file.document_id = 'saved'
    form.value.attachments = []; form.value.number = ''
    notice.value = 'Dokument z załącznikami został dodany. Znajdziesz go w zakładce Dokumenty.'
    emit('saved')
    selected.value = await props.request(`/inbox/${id}`)
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
onMounted(async () => { busy.value = true; try { await load() } catch (cause) { error.value = cause.message } finally { busy.value = false } })
</script>

<template>
  <section class="inbox-panel" aria-label="Bufor poczty">
    <div class="inbox-toolbar"><p>Wybierz wiadomość i dodaj jej załączniki do dokumentów.</p><button class="primary" :disabled="busy || loading" @click="sync">{{ busy ? 'Przetwarzanie…' : 'Odbierz pocztę' }}</button></div>
    <p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
    <div class="inbox-columns">
      <section class="inbox-list" aria-label="Lista wiadomości">
        <button v-for="item in messages" :key="item.id" class="inbox-message" :class="{ chosen: selected?.id === item.id }" :aria-pressed="selected?.id === item.id" :disabled="busy" @click="open(item)">
          <strong>{{ item.subject || '(bez tematu)' }}</strong><span>{{ item.sender }}</span><small>{{ date(item.received_at) }}</small><p>{{ item.preview }}</p>
        </button>
        <p v-if="!messages.length" class="empty">{{ busy ? 'Wczytywanie…' : 'Brak wiadomości. Kliknij „Odbierz pocztę”. Ustawienia skrzynki znajdziesz w Ustawienia → Poczta → IMAP.' }}</p>
        <div class="inbox-pages"><button class="text-button" :disabled="busy || offset === 0" @click="page(-1)">Poprzednie</button><span>{{ offset / 50 + 1 }}</span><button class="text-button" :disabled="busy || !hasMore" @click="page(1)">Następne</button></div>
      </section>
      <section class="inbox-preview" aria-label="Podgląd wiadomości" :aria-busy="loading">
        <p v-if="loading" role="status">Wczytywanie wiadomości…</p>
        <template v-else-if="selected">
          <h2>{{ selected.subject || '(bez tematu)' }}</h2><p>{{ selected.sender }}<br /><small>{{ date(selected.received_at) }}</small></p>
          <pre class="inbox-body">{{ selected.body || 'Wiadomość nie zawiera treści tekstowej.' }}</pre>
          <form v-if="selected.attachments.length" class="inbox-import" @submit.prevent="save">
            <h3>Dodaj dokument z załączników</h3>
            <p v-if="selected.attachment_prefix">Do dodania kwalifikują się pliki z prefiksem „{{ selected.attachment_prefix }}”.</p>
            <fieldset :disabled="busy"><legend>Załączniki (wybierz maksymalnie 10)</legend>
              <div v-for="file in selected.attachments" :key="file.id" class="inbox-file">
                <label><input v-model="form.attachments" type="checkbox" :value="file.id" :disabled="!!file.document_id || file.eligible === false" />{{ file.name }} <small>({{ Math.ceil(file.size / 1024) }} KB){{ file.document_id ? ' — dodano do dokumentu' : file.eligible === false ? ' — inny prefiks' : '' }}</small></label>
                <button type="button" class="text-button" @click="download(file)">Pobierz</button>
              </div>
              <div class="grid">
                <label>Firma / klient<select v-model="form.company_id" required><option value="" disabled>Wybierz z listy</option><option v-for="client in clients" :key="client.id" :value="client.id">{{ client.name }}{{ client.employer_name ? ` — ${client.employer_name}` : '' }}</option></select></label>
                <label>Rodzaj dokumentu<select v-model="form.document_type_id" required><option value="" disabled>Wybierz rodzaj</option><option v-for="type in types" :key="type.id" :value="type.id">{{ type.name }}</option></select></label>
                <label>Numer dokumentu<input v-model="form.number" required maxlength="100" /></label>
              </div>
              <button class="primary" :disabled="!form.attachments.length || form.attachments.length > 10">{{ busy ? 'Zapisywanie…' : 'Dodaj dokument' }}</button>
            </fieldset>
          </form>
          <p v-else>Brak załączników do dodania. Starsze wiadomości mogą wymagać ponownego odbioru poczty.</p>
        </template>
        <p v-else class="empty">Wybierz wiadomość z listy po lewej stronie.</p>
      </section>
    </div>
  </section>
</template>

<style scoped>
.inbox-toolbar,.inbox-pages,.inbox-file{display:flex;align-items:center;justify-content:space-between;gap:12px}.inbox-toolbar{margin-bottom:20px}.inbox-columns{display:grid;grid-template-columns:minmax(240px,32%) minmax(0,1fr);gap:20px;align-items:start}.inbox-list,.inbox-preview{border:1px solid var(--line,#d7dfd9);border-radius:16px;min-width:0;background:var(--theme-surface,#fff)}.inbox-list{max-height:75vh;overflow:auto}.inbox-preview{padding:24px}.inbox-message{display:block;width:100%;text-align:left;padding:16px;border:0;border-bottom:1px solid var(--line,#d7dfd9);border-radius:0;background:transparent;color:inherit;cursor:pointer;overflow-wrap:anywhere}.inbox-message strong,.inbox-message span,.inbox-message small{display:block}.inbox-message p{font-size:13px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}.inbox-message.chosen{background:var(--theme-soft,#edf2e9);box-shadow:inset 4px 0 #52654a}.inbox-body{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;line-height:1.6;max-height:45vh;overflow:auto;padding:16px 0}.inbox-preview h2,.inbox-preview>p{overflow-wrap:anywhere}.inbox-import{border-top:1px solid var(--line,#d7dfd9);padding-top:16px}.inbox-import fieldset{border:0;padding:0;min-width:0}.inbox-file{margin:12px 0;overflow-wrap:anywhere}.inbox-file label{display:block;min-width:0}.inbox-file input{display:inline-block;vertical-align:middle;width:auto;margin-right:8px}.inbox-import .grid{margin:20px 0}.inbox-pages{padding:12px}.inbox-message:focus-visible{outline:2px solid #52654a;outline-offset:-3px}@media(max-width:850px){.inbox-columns{grid-template-columns:1fr}.inbox-list{max-height:35vh}.inbox-preview{padding:16px}.inbox-toolbar{align-items:start;flex-direction:column}}
</style>
