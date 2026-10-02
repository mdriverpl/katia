<script setup>
import StatusBadge from './StatusBadge.vue'
import { computed, ref, watch } from 'vue'
import FilePreview from './FilePreview.vue'
import FileTypeTile from './FileTypeTile.vue'
import DeadlineTypeAutocomplete from './DeadlineTypeAutocomplete.vue'
import { ArrowLeft, Download, FileText, Pencil, Plus, X } from 'lucide-vue-next'
const props = defineProps({ documents: Array, clients: Array, types: Array, request: Function, clientFilter: String, canDelete: Boolean, fixedClientId: String })
const emit = defineEmits(['saved', 'download', 'cancelled'])
const preview = ref(null)
const query = ref('')
const typeFilter = ref('')
const statusFilter = ref('')
const client = ref(props.clientFilter || '')
const clientSearch = ref(props.clients.find(item => item.id === client.value)?.name || '')
watch(() => props.clientFilter, value => {
  client.value = value || ''
  clientSearch.value = props.clients.find(item => item.id === client.value)?.name || ''
})
function searchClient(value) { clientSearch.value = value; client.value = '' }
const visible = ref(false)
const busy = ref(false)
const error = ref('')
const editing = ref(null)
const savedId = ref(null)
const files = ref([])
const existingFiles = ref([])
const form = ref({})
const fileSize = size => size < 1024 ? `${size} B` : size < 1024 * 1024 ? `${(size / 1024).toLocaleString('pl-PL', { maximumFractionDigits: 1 })} KB` : `${(size / (1024 * 1024)).toLocaleString('pl-PL', { maximumFractionDigits: 1 })} MB`
const statuses = computed(() => [...new Set(['nowy', 'w trakcie', 'gotowy', 'wydany', ...props.documents.map(item => item.status)])])
const filtered = computed(() => props.documents.filter(item => {
  const clientName = props.clients.find(entry => entry.id === item.company_id)?.name || ''
  return (client.value ? item.company_id === client.value : clientName.toLocaleLowerCase('pl-PL').includes(clientSearch.value.trim().toLocaleLowerCase('pl-PL'))) && (!typeFilter.value || item.document_type_id === typeFilter.value) && (!statusFilter.value || item.status === statusFilter.value) && `${item.title} ${clientName}`.toLocaleLowerCase('pl-PL').includes(query.value.trim().toLocaleLowerCase('pl-PL'))
}))
function open(item = null) {
  if (visible.value) return
  editing.value = item?.id || null
  savedId.value = null
  form.value = { company_id: item?.company_id || client.value, title: item?.title || '', number: item?.number || '', document_type_id: item?.document_type_id || null, status: item?.status || 'nowy', terms: item?.terms?.map(term => ({ ...term })) || (item?.due_date ? [{ description: item.title, due_date: item.due_date, calendar: 'both' }] : []) }
  files.value = []; existingFiles.value = item?.files || []; error.value = ''; visible.value = true
}
function chooseFiles(event) {
  const selected = [...files.value, ...Array.from(event.target.files)]
  event.target.value = ''
  if (selected.length > 10 || selected.some(file => file.size > 20 * 1024 * 1024)) { error.value = 'Do 10 nowych plików jednocześnie, każdy do 20 MB.'; return }
  files.value = selected; error.value = ''
}
async function save() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    if (!savedId.value) {
      const result = await props.request(editing.value ? `/documents/${editing.value}` : '/documents', { method: editing.value ? 'PUT' : 'POST', body: JSON.stringify(form.value) })
      savedId.value = result.id
    }
    if (files.value.length) {
      const body = new FormData()
      files.value.forEach(file => body.append('files', file))
      await props.request(`/documents/${savedId.value}/files`, { method: 'POST', body })
      files.value = []
    }
    visible.value = false; emit('saved')
  } catch (cause) { error.value = savedId.value ? `Dokument zapisano. Wysyłanie plików: ${cause.message} Możesz ponowić zapis.` : cause.message }
  finally { busy.value = false }
}
function close() { visible.value = false; if (savedId.value) emit('saved'); else emit('cancelled') }
async function remove(item) {
  if (busy.value || !confirm(`Usunąć dokument „${item.title}” wraz z plikami i terminami? Tej operacji nie można cofnąć.`)) return
  busy.value = true; error.value = ''
  try {
    const result = await props.request(`/documents/${item.id}`, { method: 'DELETE' })
    if (result.cleanup_warning) error.value = result.cleanup_warning
    emit('saved')
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
defineExpose({ open, close, busy })
</script>

<template>
  <FilePreview ref="preview" :request="request" />
  <template v-if="!visible">
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div class="document-filters">
      <label>Szukaj nazwy dokumentu lub klienta<input v-model="query" type="search" placeholder="Wpisz nazwę…" /></label>
      <DeadlineTypeAutocomplete id="document-client-filter" label="Klient" :model-value="clientSearch" :options="clients" :required="false" :maxlength="255" placeholder="Wpisz nazwę klienta…" empty-message="Nie znaleziono klienta." @update:model-value="searchClient" @selected="client = $event.id" />
      <label>Rodzaj dokumentu<select v-model="typeFilter"><option value="">Wszystkie rodzaje</option><option v-for="item in types" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
      <label>Status<select v-model="statusFilter"><option value="">Wszystkie statusy</option><option v-for="status in statuses" :key="status">{{ status }}</option></select></label>
      <button class="text-button" @click="query = ''; client = ''; clientSearch = ''; typeFilter = ''; statusFilter = ''">Wyczyść filtry</button>
    </div>
    <p class="form-hint">Dokumentów: {{ filtered.length }}</p>
    <section class="table data-list documents-list" aria-label="Dokumenty">
      <table v-if="filtered.length"><thead><tr><th scope="col">Nazwa / klient</th><th scope="col">Rodzaj / numer</th><th scope="col">Status</th><th scope="col">Terminy</th><th scope="col">Pliki</th><th scope="col">Akcje</th></tr></thead>
        <tbody><tr v-for="item in filtered" :key="item.id">
          <td><strong>{{ item.title }}</strong><small>{{ clients.find(entry => entry.id === item.company_id)?.name }}</small></td>
          <td>{{ types.find(entry => entry.id === item.document_type_id)?.name || 'Nie wybrano' }}<small>{{ item.number || '—' }}</small></td>
          <td><StatusBadge :status="item.status" /></td>
          <td><template v-if="item.terms?.length"><small v-for="(term, index) in item.terms" :key="index">{{ term.due_date }} · {{ term.description }}</small></template><span v-else>{{ item.due_date || '—' }}</span></td>
          <td><div v-if="item.files.length" class="file-type-tiles"><FileTypeTile v-for="file in item.files" :key="file.id" :file="file" @preview="preview.open(item.id, file)" /></div><span v-else>—</span></td>
          <td><button class="text-button" @click="open(item)"><Pencil :size="14" />Edytuj</button><button class="text-button" @click="open(item)"><Plus :size="14" />Dodaj pliki</button><button v-if="canDelete" class="text-button" :disabled="busy" @click="remove(item)">Usuń</button></td>
        </tr></tbody>
      </table><p v-else class="empty">Brak dokumentów pasujących do filtrów.</p>
    </section>
  </template>
  <form v-else class="entry-form compact-service-form service-template-page" @submit.prevent="save">
    <button type="button" class="text-button" :disabled="busy" @click="close"><ArrowLeft :size="16" />Wróć do listy</button>
    <h2>{{ editing ? 'Edytuj dokument' : 'Dodaj dokument' }}</h2>
    <fieldset class="service-fields" :disabled="busy || !!savedId">
      <label>Klient<select v-model="form.company_id" required :disabled="!!fixedClientId"><option value="" disabled>Wybierz klienta</option><option v-for="item in clients" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
      <label>Rodzaj dokumentu<select v-model="form.document_type_id"><option :value="null">Nie wybrano</option><option v-for="item in types" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
      <label>Nazwa<input v-model="form.title" required maxlength="255" /></label><label>Numer<input v-model="form.number" maxlength="100" /></label>
      <label>Status<select v-model="form.status"><option v-for="status in statuses" :key="status">{{ status }}</option></select></label>
      <div class="service-heading"><h3>Terminy dokumentu</h3><button type="button" class="text-button" :disabled="form.terms.length >= 50" @click="form.terms.push({ description: '', due_date: '', calendar: 'both' })"><Plus :size="16" />Dodaj termin</button></div>
      <div v-for="(term, index) in form.terms" :key="index" class="document-term-row">
        <label>Opis<input v-model="term.description" required maxlength="500" /></label><label>Data<input v-model="term.due_date" type="date" required /></label>
        <label>Kalendarz<select v-model="term.calendar"><option value="both">Klienta i operatora</option><option value="client">Tylko klienta</option><option value="operator">Tylko operatora</option></select></label>
        <button type="button" class="icon-button" :aria-label="'Usuń termin ' + (index + 1)" @click="form.terms.splice(index, 1)"><X :size="16" /></button>
      </div>
    </fieldset>
    <div v-if="existingFiles.length" class="attachment-tiles"><button v-for="file in existingFiles" :key="file.id" type="button" class="attachment-tile" :title="file.name" :aria-label="'Podgląd ' + file.name" @click="preview.open(editing, file)"><FileText :size="20" aria-hidden="true" /><span class="attachment-tile-text"><span class="attachment-tile-name">{{ file.name }}</span><span class="attachment-tile-size">{{ fileSize(file.size) }}</span></span><Download :size="14" aria-hidden="true" /></button></div>
    <label>Dodaj pliki<input type="file" multiple :disabled="busy" @change="chooseFiles" /><small>Możesz wybierać pliki kilka razy. Do 10 nowych plików na zapis, każdy do 20 MB.</small></label>
    <ul v-if="files.length" class="attachment-tiles" aria-label="Pliki do wysłania"><li v-for="(file, index) in files" :key="index" class="attachment-tile attachment-tile-pending" :title="file.name"><FileText :size="20" aria-hidden="true" /><span class="attachment-tile-text"><span class="attachment-tile-name">{{ file.name }}</span><span class="attachment-tile-size">{{ fileSize(file.size) }} · Do wysłania</span></span><button type="button" class="attachment-tile-remove" :aria-label="'Usuń z kolejki ' + file.name" :disabled="busy" @click="files.splice(index, 1)"><X :size="14" /></button></li></ul>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div class="service-page-actions"><button class="primary" :disabled="busy">{{ busy ? 'Zapisywanie…' : savedId ? 'Ponów wysyłanie plików' : 'Zapisz dokument' }}</button><button type="button" class="text-button" :disabled="busy" @click="close">Anuluj</button></div>
  </form>
</template>
