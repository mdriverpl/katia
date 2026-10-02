<script setup>
import StatusBadge from './StatusBadge.vue'
import { computed, nextTick, ref, watch } from 'vue'
import { Plus } from 'lucide-vue-next'
import DocumentsPanel from './DocumentsPanel.vue'
import InboxPanel from './InboxPanel.vue'
import ClientServicesPanel from './ClientServicesPanel.vue'
import FilePreview from './FilePreview.vue'
import FileTypeTile from './FileTypeTile.vue'
const props = defineProps({ clientId: String, documents: Array, services: Array, clients: Array, templates: Array, documentTypes: Array, deadlineTypes: Array, request: Function })
const emit = defineEmits(['saved'])
const action = ref('')
const editor = ref(null)
const documentDialog = ref(null)
const buffer = ref(null)
const modalBusy = computed(() => !!editor.value?.busy || !!buffer.value?.busy || !!buffer.value?.loading)
const refresh = ref(0)
const saving = ref(false)
const actionError = ref('')
const term = ref({ title: '', due_date: '', notes: '' })
async function add() {
  action.value = tab.value; actionError.value = ''
  term.value = { title: '', due_date: '', notes: '' }
  await nextTick()
  if (action.value === 'Dokumenty') { editor.value?.open(); await nextTick(); documentDialog.value?.showModal() }
  if (action.value === 'Usługi') editor.value?.open(null, props.clientId)
}
async function addFromBuffer() {
  action.value = 'Bufor'
  await nextTick()
  documentDialog.value?.showModal()
}
function closeDocumentModal() {
  if (modalBusy.value) return
  if (action.value === 'Dokumenty') editor.value?.close()
  else action.value = ''
}
function saved() { action.value = ''; refresh.value++; emit('saved') }
async function saveTerm() {
  if (saving.value) return
  saving.value = true; actionError.value = ''
  try { await props.request('/deadlines', { method: 'POST', body: JSON.stringify({ ...term.value, company_id: props.clientId }) }); saved() }
  catch (cause) { actionError.value = cause.message }
  finally { saving.value = false }
}
const tab = ref('Terminy')
const terms = ref([])
const loading = ref(false)
const error = ref('')
const preview = ref(null)
const documents = computed(() => props.documents.filter(item => item.company_id === props.clientId))
const services = computed(() => props.services.filter(item => item.company_id === props.clientId))
watch([() => props.clientId, refresh], async ([id], _, onCleanup) => {
  let cancelled = false
  onCleanup(() => { cancelled = true })
  terms.value = []; error.value = ''; loading.value = false
  if (!id) return
  loading.value = true
  try { const result = await props.request(`/companies/${id}/deadlines`); if (!cancelled) terms.value = result }
  catch (cause) { if (!cancelled) error.value = cause.message }
  finally { if (!cancelled) loading.value = false }
}, { immediate: true })
const date = value => value ? new Date(value + 'T12:00:00').toLocaleDateString('pl-PL') : 'Data do ustalenia'
const money = value => value == null ? 'Cena nieustalona' : new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(Number(value))
</script>

<template>
  <section class="client-related" aria-label="Powiązane dane klienta">
    <div v-if="!action" class="client-related-tabs" aria-label="Wybierz dane klienta"><button v-for="name in ['Terminy', 'Dokumenty', 'Usługi']" :key="name" type="button" :aria-pressed="tab === name" :class="{ selected: tab === name }" @click="tab = name">{{ name }}</button></div>
    <p v-if="!clientId" class="empty">Zapisz klienta, aby wyświetlić jego terminy, dokumenty i usługi.</p>
    <div v-else-if="action && !['Dokumenty', 'Bufor'].includes(action)" class="client-quick-editor">
      <ClientServicesPanel v-if="action === 'Usługi'" ref="editor" :clients="clients" :services="services" :templates="templates" :deadline-types="deadlineTypes" :request="request" @saved="saved" @cancelled="action = ''" />
      <form v-else class="service-template-page compact-service-form" @submit.prevent="saveTerm"><h3>Dodaj termin</h3><p class="form-hint">Klient: {{ clients.find(item => item.id === clientId)?.name }}</p><fieldset class="service-fields" :disabled="saving"><label>Opis<input v-model="term.title" required maxlength="255" /></label><label>Data<input v-model="term.due_date" type="date" required /></label><label class="service-description-field">Notatki<textarea v-model="term.notes" rows="2" /></label></fieldset><p v-if="actionError" class="error" role="alert">{{ actionError }}</p><div class="service-page-actions"><button class="primary" :disabled="saving">{{ saving ? 'Zapisywanie…' : 'Zapisz termin' }}</button><button type="button" class="text-button" :disabled="saving" @click="action = ''">Anuluj</button></div></form>
    </div>
    <div v-else class="client-related-content">
      <div class="client-related-toolbar"><button type="button" class="text-button" @click="add"><Plus :size="16" />{{ tab === 'Terminy' ? 'Dodaj termin' : tab === 'Dokumenty' ? 'Dodaj dokument' : 'Dodaj usługę' }}</button><button v-if="tab === 'Dokumenty'" type="button" class="text-button" @click="addFromBuffer"><Plus :size="16" />Dodaj z bufora</button></div>
      <template v-if="tab === 'Terminy'">
        <p v-if="loading" role="status">Wczytywanie terminów…</p><p v-else-if="error" class="error" role="alert">{{ error }}</p>
        <template v-else>
          <div v-if="terms.length" class="client-related-table-wrap"><table class="client-related-table" aria-label="Terminy klienta">
            <thead><tr><th scope="col">Termin / adres</th><th scope="col">Data / godzina</th><th scope="col">Status</th></tr></thead>
            <tbody><tr v-for="item in terms" :key="item.id"><td><strong>{{ item.title }}</strong><small v-if="item.address">{{ item.address }}</small></td><td>{{ date(item.due_date) }}<small v-if="item.scheduled_time">{{ item.scheduled_time }}</small></td><td><StatusBadge :status="item.status" :due-date="item.due_date" /></td></tr></tbody>
          </table></div><p v-else class="empty">Brak terminów klienta.</p>
        </template>
      </template>
      <template v-else-if="tab === 'Dokumenty'">
        <div v-if="documents.length" class="client-related-table-wrap"><table class="client-related-table" aria-label="Dokumenty klienta">
          <thead><tr><th scope="col">Dokument / numer</th><th scope="col">Status</th><th scope="col">Pliki</th></tr></thead>
          <tbody><tr v-for="item in documents" :key="item.id"><td><strong>{{ item.title }}</strong><small>{{ item.number || 'Bez numeru' }}</small></td><td><StatusBadge :status="item.status" /></td><td><div v-if="item.files.length" class="file-type-tiles"><FileTypeTile v-for="file in item.files" :key="file.id" :file="file" @preview="preview.open(item.id, file)" /></div><span v-else>—</span></td></tr></tbody>
        </table></div><p v-else class="empty">Brak dokumentów klienta.</p>
      </template>
      <template v-else>
        <div v-if="services.length" class="client-related-table-wrap"><table class="client-related-table" aria-label="Usługi klienta">
          <thead><tr><th scope="col">Usługa</th><th scope="col">Cena</th><th scope="col">Realizacja</th></tr></thead>
          <tbody><tr v-for="item in services" :key="item.id"><td><strong>{{ item.name }}</strong></td><td>{{ money(item.price) }}</td><td><div class="service-progress"><StatusBadge :progress="item.progress || 0" /><progress :value="item.progress || 0" max="100" :aria-label="'Realizacja ' + item.name" /><small>{{ item.progress || 0 }}%</small></div></td></tr></tbody>
        </table></div><p v-else class="empty">Brak usług klienta.</p>
      </template>
    </div>
    <dialog v-if="clientId && ['Dokumenty', 'Bufor'].includes(action)" ref="documentDialog" class="client-document-dialog" :class="{ 'buffer-dialog': action === 'Bufor' }" aria-labelledby="client-document-modal-title" @cancel.prevent="closeDocumentModal" @click.self="closeDocumentModal">
      <div class="client-document-shell">
        <header class="client-document-modal-header"><h2 id="client-document-modal-title">{{ action === 'Bufor' ? 'Dodaj dokument z bufora' : 'Dodaj dokument' }}</h2><button type="button" class="text-button" :disabled="modalBusy" @click="closeDocumentModal">Zamknij</button></header>
        <p class="form-hint">Firma / klient: {{ clients.find(item => item.id === clientId)?.name }}</p>
        <DocumentsPanel v-if="action === 'Dokumenty'" ref="editor" :clients="clients" :documents="documents" :types="documentTypes" :client-filter="clientId" :fixed-client-id="clientId" :request="request" @saved="saved" @cancelled="action = ''" />
        <InboxPanel v-else ref="buffer" :clients="clients" :types="documentTypes" :fixed-client-id="clientId" :request="request" @saved="saved" />
      </div>
    </dialog>
    <FilePreview ref="preview" :request="request" />
  </section>
</template>
<style scoped>
.client-document-dialog{width:min(820px,calc(100vw - 32px));max-height:92svh;padding:0;border:1px solid var(--line);border-radius:16px;background:var(--theme-surface,#fff);color:inherit;box-shadow:0 20px 70px #0004}.client-document-dialog.buffer-dialog{width:min(1280px,calc(100vw - 32px))}.client-document-dialog::backdrop{background:#102e2877}.client-document-shell{padding:24px}.client-document-modal-header{display:flex;align-items:center;justify-content:space-between;gap:16px}.client-document-modal-header h2{margin:0}.client-document-shell>.form-hint{margin:12px 0 20px}.client-document-shell :deep(.service-template-page){border:0;padding:0;box-shadow:none}.client-related-toolbar{display:flex;flex-wrap:wrap;gap:8px}@media(max-width:600px){.client-document-shell{padding:16px}}
</style>
