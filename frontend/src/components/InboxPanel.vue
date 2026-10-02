<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import InboxAttachmentPreview, { previewType } from './InboxAttachmentPreview.vue'
import DeadlineTypeAutocomplete from './DeadlineTypeAutocomplete.vue'
const props = defineProps({ request: Function, clients: Array, types: Array, fixedClientId: String })
const emit = defineEmits(['saved'])
const messages = ref([]), selected = ref(null), busy = ref(false), loading = ref(false)
const error = ref(''), notice = ref(''), offset = ref(0), hasMore = ref(false)
const form = ref({ company_id: '', document_type_id: '', number: '', attachments: [] })
const previewFile = ref(null)
const importDialog = ref(null), clientSearch = ref('')
const clientOptions = computed(() => props.clients.map(client => ({ ...client, name: [client.name, client.employer_name, client.email].filter(Boolean).join(' — ') })))
const availableFiles = computed(() => (selected.value?.attachments || []).filter(file => !file.document_id && file.eligible !== false))
function searchClient(value) { clientSearch.value = value; form.value.company_id = '' }
function openImport() {
  if (busy.value || !availableFiles.value.length) return
  error.value = ''
  if (!form.value.attachments.length) form.value.attachments = availableFiles.value.slice(0, 10).map(file => file.id)
  importDialog.value.showModal()
  importDialog.value.querySelector('[role="combobox"]')?.focus()
}
function closeImport() { if (!busy.value) importDialog.value?.close() }
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
  loading.value = true; selected.value = null; previewFile.value = null; error.value = ''; notice.value = ''
  clientSearch.value = ''
  try {
    const result = await props.request(`/inbox/${item.id}`)
    if (current !== generation) return
    selected.value = result
    previewFile.value = result.attachments.find(file => file.eligible !== false && previewType(file.name)) || result.attachments.find(file => previewType(file.name)) || result.attachments[0] || null
    form.value = { company_id: props.fixedClientId || '', document_type_id: '', number: '', attachments: result.attachments.filter(file => !file.document_id && file.eligible !== false).slice(0, 10).map(file => file.id) }
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
  if (busy.value) return
  if (!props.clients.some(client => client.id === form.value.company_id)) { error.value = 'Wybierz firmę / klienta z podpowiedzi.'; return }
  busy.value = true; error.value = ''; notice.value = ''
  const id = selected.value.id
  try {
    const result = await props.request(`/inbox/${id}/documents`, { method: 'POST', body: JSON.stringify(form.value) })
    // Mark success immediately, even if refreshing the detail fails afterwards.
    selected.value.attachments = selected.value.attachments.filter(file => !form.value.attachments.includes(file.id))
    previewFile.value = selected.value.attachments.find(file => previewType(file.name)) || selected.value.attachments[0] || null
    form.value.attachments = []; form.value.number = ''
    notice.value = 'Dokument z załącznikami został dodany. Znajdziesz go w zakładce Dokumenty.'
    importDialog.value?.close()
    if (result.buffer_removed) {
      selected.value = null; previewFile.value = null
      messages.value = messages.value.filter(item => item.id !== id)
      if (!messages.value.length && offset.value) offset.value = Math.max(0, offset.value - 50)
    }
    emit('saved')
    await load()
    if (!result.buffer_removed) selected.value = await props.request(`/inbox/${id}`)
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
onMounted(async () => { busy.value = true; try { await load() } catch (cause) { error.value = cause.message } finally { busy.value = false } })
defineExpose({ busy, loading })
</script>

<template>
  <section class="inbox-panel" aria-label="Bufor poczty">
    <div class="inbox-toolbar"><p>Wiadomości z ostatnich 24 godzin. Wybierz wiadomość i dodaj jej załączniki do dokumentów.</p><button class="primary" :disabled="busy || loading" @click="sync">{{ busy ? 'Przetwarzanie…' : 'Odbierz pocztę' }}</button></div>
    <p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
    <div class="inbox-columns">
      <section class="inbox-list" aria-label="Lista wiadomości">
        <button v-for="item in messages" :key="item.id" class="inbox-message" :class="{ chosen: selected?.id === item.id }" :aria-pressed="selected?.id === item.id" :disabled="busy" @click="open(item)">
          <strong>{{ item.subject || '(bez tematu)' }}</strong><span>{{ item.sender }}</span><small>{{ date(item.received_at) }}</small><p>{{ item.preview }}</p>
        </button>
        <p v-if="!messages.length" class="empty">{{ busy ? 'Wczytywanie…' : 'Brak wiadomości do obsłużenia z ostatnich 24 godzin. Kliknij „Odbierz pocztę”. Ustawienia skrzynki znajdziesz w Ustawienia → Poczta → IMAP.' }}</p>
        <div class="inbox-pages"><button class="text-button" :disabled="busy || offset === 0" @click="page(-1)">Poprzednie</button><span>{{ offset / 50 + 1 }}</span><button class="text-button" :disabled="busy || !hasMore" @click="page(1)">Następne</button></div>
      </section>
      <section class="inbox-preview" aria-label="Podgląd wiadomości" :aria-busy="loading">
        <p v-if="loading" role="status">Wczytywanie wiadomości…</p>
        <template v-else-if="selected">
          <div class="inbox-message-heading"><h2>{{ selected.subject || '(bez tematu)' }}</h2><button type="button" class="primary" :disabled="busy || !availableFiles.length" @click="openImport">Dodaj dokument</button></div><p>{{ selected.sender }}<br /><small>{{ date(selected.received_at) }}</small></p>
          <div v-if="selected.attachments.length" class="attachment-tabs" aria-label="Wybierz plik do podglądu">
            <button v-for="file in selected.attachments" :key="file.id" type="button" class="text-button" :class="{ active: previewFile?.id === file.id }" :aria-pressed="previewFile?.id === file.id" @click="previewFile = file">{{ file.name }}</button>
          </div>
          <InboxAttachmentPreview :message-id="selected.id" :file="previewFile" :request="request" @download="download" />
          <details :key="selected.id" class="message-body-details" :open="!selected.attachments.length"><summary>Treść wiadomości</summary><pre class="inbox-body">{{ selected.body || 'Wiadomość nie zawiera treści tekstowej.' }}</pre></details>
          <dialog v-if="selected.attachments.length" ref="importDialog" class="inbox-import-dialog" aria-labelledby="inbox-import-title" @cancel="busy && $event.preventDefault()" @click.self="closeImport">
          <form class="inbox-import entry-form" @submit.prevent="save">
            <div class="inbox-message-heading"><h2 id="inbox-import-title">Dodaj dokument</h2><button type="button" class="text-button" :disabled="busy" @click="closeImport">Zamknij</button></div>
            <p v-if="selected.attachment_prefix">Do dodania kwalifikują się pliki z prefiksem „{{ selected.attachment_prefix }}”.</p>
            <fieldset :disabled="busy"><legend>Załączniki (wybierz maksymalnie 10)</legend>
              <div v-for="file in selected.attachments" :key="file.id" class="inbox-file">
                <label><input v-model="form.attachments" type="checkbox" :value="file.id" :disabled="!!file.document_id || file.eligible === false" />{{ file.name }} <small>({{ Math.ceil(file.size / 1024) }} KB){{ file.document_id ? ' — dodano do dokumentu' : file.eligible === false ? ' — inny prefiks' : '' }}</small></label>
                <div class="attachment-actions"><button type="button" class="text-button" @click="previewFile = file; closeImport()">Podgląd</button><button type="button" class="text-button" @click="download(file)">Pobierz</button></div>
              </div>
              <div class="grid">
                <div v-if="fixedClientId" class="inbox-client-field"><label>Firma / klient<input :value="clients.find(client => client.id === fixedClientId)?.name" readonly /></label></div>
                <div v-else class="inbox-client-field"><DeadlineTypeAutocomplete id="inbox-document-client" label="Firma / klient" :model-value="clientSearch" :options="clientOptions" :maxlength="800" placeholder="Wpisz nazwę, imię, nazwisko lub e-mail…" empty-message="Nie znaleziono firmy / klienta. Wybierz istniejącą pozycję z listy." @update:model-value="searchClient" @selected="form.company_id = $event.id" /><small>Wybierz pozycję z podpowiedzi.</small></div>
                <label>Rodzaj dokumentu<select v-model="form.document_type_id" required><option value="" disabled>Wybierz rodzaj</option><option v-for="type in types" :key="type.id" :value="type.id">{{ type.name }}</option></select></label>
                <label>Numer dokumentu<input v-model="form.number" required maxlength="100" /></label>
              </div>
              <p v-if="error" class="error" role="alert">{{ error }}</p>
              <div class="inbox-modal-actions"><button type="submit" class="primary" :disabled="!form.attachments.length || form.attachments.length > 10">{{ busy ? 'Zapisywanie…' : 'Zapisz dokument' }}</button><button type="button" class="text-button" @click="closeImport">Anuluj</button></div>
            </fieldset>
          </form>
          </dialog>
          <p v-if="!selected.attachments.length">Brak załączników do dodania. Starsze wiadomości mogą wymagać ponownego odbioru poczty.</p>
        </template>
        <p v-else class="empty">Wybierz wiadomość z listy po lewej stronie.</p>
      </section>
    </div>
  </section>
</template>

<style scoped>
.inbox-message-heading{display:flex;align-items:center;justify-content:space-between;gap:16px}.inbox-message-heading h2{min-width:0;overflow-wrap:anywhere}.inbox-message-heading>.primary{flex-shrink:0}
.inbox-import-dialog{padding:0;width:min(760px,calc(100vw - 32px));max-height:90svh;overflow:auto;border:1px solid var(--line);border-radius:16px;background:var(--theme-surface,#fff);color:inherit;box-shadow:0 20px 70px #0004}.inbox-import-dialog::backdrop{background:#102e2877}
.inbox-import-dialog .inbox-import{padding:24px;border:0}.inbox-client-field{grid-column:1 / -1}.inbox-client-field>small{display:block;margin-top:6px;color:var(--muted)}.inbox-modal-actions{display:flex;gap:12px;align-items:center;margin-top:16px}
.inbox-import-dialog .inbox-file input[type="checkbox"]{width:16px;height:16px;min-height:16px;padding:0;accent-color:var(--forest)}
@media(max-width:600px){.inbox-message-heading{align-items:start;flex-direction:column}.inbox-import-dialog .inbox-import{padding:16px}.inbox-file{flex-wrap:wrap}}
.attachment-tabs{display:flex;flex-wrap:wrap;gap:6px;margin-top:16px}.attachment-tabs button{overflow-wrap:anywhere;white-space:normal;text-align:left;max-width:100%}.attachment-tabs button.active{background:var(--theme-soft,#edf2e9);box-shadow:inset 0 -2px var(--forest)}.attachment-actions{display:flex;flex-shrink:0;gap:4px}.message-body-details{margin:16px 0}.message-body-details summary{cursor:pointer;font-weight:600}
.inbox-toolbar,.inbox-pages,.inbox-file{display:flex;align-items:center;justify-content:space-between;gap:12px}.inbox-toolbar{margin-bottom:20px}.inbox-columns{display:grid;grid-template-columns:minmax(240px,32%) minmax(0,1fr);gap:20px;align-items:start}.inbox-list,.inbox-preview{border:1px solid var(--line,#d7dfd9);border-radius:16px;min-width:0;background:var(--theme-surface,#fff)}.inbox-list{max-height:75vh;overflow:auto}.inbox-preview{padding:24px}.inbox-message{display:block;width:100%;text-align:left;padding:16px;border:0;border-bottom:1px solid var(--line,#d7dfd9);border-radius:0;background:transparent;color:inherit;cursor:pointer;overflow-wrap:anywhere}.inbox-message strong,.inbox-message span,.inbox-message small{display:block}.inbox-message p{font-size:13px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}.inbox-message.chosen{background:var(--theme-soft,#edf2e9);box-shadow:inset 4px 0 #52654a}.inbox-body{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;line-height:1.6;max-height:45vh;overflow:auto;padding:16px 0}.inbox-preview h2,.inbox-preview>p{overflow-wrap:anywhere}.inbox-import{border-top:1px solid var(--line,#d7dfd9);padding-top:16px}.inbox-import fieldset{border:0;padding:0;min-width:0}.inbox-file{margin:12px 0;overflow-wrap:anywhere}.inbox-file label{display:block;min-width:0}.inbox-file input{display:inline-block;vertical-align:middle;width:auto;margin-right:8px}.inbox-import .grid{margin:20px 0}.inbox-pages{padding:12px}.inbox-message:focus-visible{outline:2px solid #52654a;outline-offset:-3px}@media(max-width:850px){.inbox-columns{grid-template-columns:1fr}.inbox-list{max-height:35vh}.inbox-preview{padding:16px}.inbox-toolbar{align-items:start;flex-direction:column}}
</style>
