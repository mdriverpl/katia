<script setup>
import StatusBadge from './StatusBadge.vue'
import { computed, nextTick, ref } from 'vue'
import { ArrowLeft, Pencil, Plus, X } from 'lucide-vue-next'
import PublicLinkDialog from './PublicLinkDialog.vue'

const props = defineProps({ services: Array, templates: Array, clients: Array, deadlineTypes: { type: Array, default: () => [] }, request: Function })
const emit = defineEmits(['saved', 'cancelled'])
const visible = ref(false)
const saving = ref(false)
const error = ref('')
const editing = ref(null)
const publicLinkDialog = ref(null)
const formHeading = ref(null)
const form = ref({ template_id: '', company_id: '' })
const selectedTemplate = computed(() => props.templates.find(item => item.id === form.value.template_id))
const appointmentKinds = computed(() => editing.value ? form.value.deadline_types : selectedTemplate.value?.deadline_types || [])
const emptyAppointment = () => ({ due_date: '', scheduled_time: '', cost: '', completed: false })
const appointments = ref([])
function selectTemplate() { appointments.value = appointmentKinds.value.map(emptyAppointment) }
function addKind() { form.value.deadline_types.push(''); appointments.value.push(emptyAppointment()) }
function removeKind(index) { form.value.deadline_types.splice(index, 1); appointments.value.splice(index, 1) }
const formatPrice = value => value == null ? 'Cena nieustalona' : new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(Number(value))
const progressStatus = value => value >= 100 ? 'Zakończona' : value > 0 ? 'W realizacji' : 'Planowana'
function open(service = null, clientId = '') {
  if (visible.value) return
  editing.value = service?.id || null
  form.value = service ? { template_id: service.template_id, company_id: service.company_id, name: service.name, price: service.price ?? '', description: service.description || '', deadline_types: [...service.deadline_types] } : { template_id: '', company_id: clientId }
  form.value.progress = service?.progress ?? 0
  appointments.value = service ? service.deadline_types.map(kind => {
    const item = (service.appointments || []).find(item => item.kind === kind)
    return { due_date: item?.due_date || '', scheduled_time: item?.scheduled_time || '', cost: item?.cost ?? '', completed: item?.completed ?? false }
  }) : []
  error.value = ''
  visible.value = true
  nextTick(() => { formHeading.value?.focus(); formHeading.value?.scrollIntoView({ block: 'start' }) })
}
async function save() {
  if (saving.value) return
  if (editing.value) {
    const types = form.value.deadline_types.map(value => value.trim())
    if (!form.value.name.trim() || types.some(value => !value) || new Set(types.map(value => value.toLocaleLowerCase('pl-PL'))).size !== types.length) {
      error.value = 'Wpisz nazwę usługi oraz różne, niepuste nazwy rodzajów terminu.'
      return
    }
  }
  saving.value = true
  error.value = ''
  try {
    const data = editing.value ? { company_id: form.value.company_id, name: form.value.name.trim(), price: form.value.price === '' ? null : String(form.value.price), description: form.value.description, deadline_types: form.value.deadline_types.map(value => value.trim()) } : form.value
    if (editing.value) data.progress = Number(form.value.progress)
    data.appointments = appointmentKinds.value.map((kind, index) => ({ kind: kind.trim(), due_date: appointments.value[index].due_date || null, scheduled_time: appointments.value[index].scheduled_time || null, cost: appointments.value[index].cost === '' ? null : String(appointments.value[index].cost), completed: appointments.value[index].completed }))
    await props.request(editing.value ? `/client-services/${editing.value}` : '/client-services', { method: editing.value ? 'PUT' : 'POST', body: JSON.stringify(data) })
    visible.value = false
    emit('saved')
  } catch (cause) { error.value = cause.message }
  finally { saving.value = false }
}
defineExpose({ open })
</script>

<template>
  <datalist id="client-service-deadline-types"><option v-for="item in deadlineTypes" :key="item.id" :value="item.name" /></datalist>
  <PublicLinkDialog ref="publicLinkDialog" :request="request" />
  <section v-if="!visible" class="table data-list client-services-list" aria-label="Usługi klientów">
    <table v-if="services.length">
      <thead><tr><th scope="col">Usługa</th><th scope="col">Klient</th><th scope="col">Cena</th><th scope="col">Realizacja</th><th scope="col">Akcje</th></tr></thead>
      <tbody><tr v-for="service in services" :key="service.id">
        <td><strong>{{ service.name }}</strong><p v-if="service.description" class="service-list-description">{{ service.description }}</p><small>Dodano: {{ new Date(service.created_at).toLocaleDateString('pl-PL') }}</small></td>
        <td>{{ clients.find(client => client.id === service.company_id)?.name || 'Nie znaleziono klienta' }}</td>
        <td>{{ formatPrice(service.price) }}</td>
        <td><div class="service-progress" :class="{ complete: service.progress === 100 }"><StatusBadge :progress="service.progress ?? 0" /><progress :value="service.progress ?? 0" max="100" :aria-label="'Postęp realizacji: ' + service.name">{{ service.progress ?? 0 }}%</progress><strong>{{ service.progress ?? 0 }}%</strong></div></td>
        <td><button class="text-button" :aria-label="'Edytuj usługę ' + service.name" @click="open(service)"><Pencil :size="15" />Edytuj</button><button class="text-button" @click="publicLinkDialog.open(service)">Link usługi</button></td>
      </tr></tbody>
    </table>
    <p v-if="!services.length" class="empty">Brak usług klientów. Kliknij „Dodaj”, wybierz rodzaj usługi i klienta.</p>
  </section>
    <form v-else class="entry-form compact-service-form service-template-page" aria-labelledby="client-service-title" @submit.prevent="save">
      <button type="button" class="text-button" :disabled="saving" @click="visible = false; emit('cancelled')"><ArrowLeft :size="16" />Wróć do listy</button>
      <div class="modal-title"><h2 id="client-service-title" ref="formHeading" tabindex="-1">{{ editing ? 'Edytuj usługę klienta' : 'Dodaj usługę klienta' }}</h2></div>
      <fieldset class="service-fields" :disabled="saving">
        <label v-if="!editing">Rodzaj usługi (szablon)<select v-model="form.template_id" required @change="selectTemplate"><option disabled value="">Wybierz szablon</option><option v-for="template in templates" :key="template.id" :value="template.id">{{ template.name }}</option></select></label>
        <p v-if="!editing && !templates.length" class="form-hint">Najpierw dodaj szablon w sekcji „Rodzaje usług”.</p>
        <label>Klient<select v-model="form.company_id" required><option disabled value="">Wybierz klienta</option><option v-for="client in clients" :key="client.id" :value="client.id">{{ client.name }}</option></select></label>
        <p v-if="!clients.length" class="form-hint">Najpierw dodaj klienta w sekcji „Klienci”.</p>
        <template v-if="editing">
          <label>Nazwa usługi<input v-model="form.name" required maxlength="255" /></label>
          <label>Cena (PLN)<input v-model="form.price" type="number" min="0" max="9999999999.99" step="0.01" placeholder="Nieustalona" /></label>
          <label>Postęp realizacji (%)<input v-model.number="form.progress" type="number" min="0" max="100" step="1" required /><small class="form-hint">{{ progressStatus(form.progress) }}</small></label>
          <label class="service-description-field">Opis<textarea v-model="form.description" rows="2" /></label>
          <div class="service-heading"><h3>Rodzaje terminu</h3><button type="button" class="text-button" :disabled="form.deadline_types.length >= 30" @click="addKind"><Plus :size="16" />Dodaj rodzaj</button></div>
        </template>
        <section v-for="(kind, index) in appointmentKinds" :key="index" class="appointment-editor">
          <div v-if="editing" class="type-editor"><label :for="'client-service-type-' + index">Rodzaj {{ index + 1 }}</label><input :id="'client-service-type-' + index" v-model="form.deadline_types[index]" list="client-service-deadline-types" required maxlength="100" /><button type="button" class="icon-button" :aria-label="'Usuń rodzaj ' + (index + 1)" @click="removeKind(index)"><X :size="16" /></button></div>
          <h3 v-else>{{ kind }}</h3>
          <label class="appointment-completed"><input v-model="appointments[index].completed" type="checkbox" />Termin wykonany</label>
          <div class="grid"><label>Data<input v-model="appointments[index].due_date" type="date" :required="!!appointments[index].scheduled_time" /></label><label>Godzina<input v-model="appointments[index].scheduled_time" type="text" maxlength="100" placeholder="np. 9:00–12:00 lub do ustalenia" /></label><label>Koszt (PLN)<input v-model="appointments[index].cost" type="number" min="0" max="9999999999.99" step="0.01" placeholder="Nieustalony" /></label></div>
        </section>
        <p v-if="appointmentKinds.length" class="form-hint">Terminy z datą pojawią się w kalendarzu. Koszty poszczególnych terminów zapisujesz osobno od ceny całej usługi.</p>
        <section v-if="!editing && selectedTemplate" class="service-card"><h3>{{ selectedTemplate.name }}</h3><strong>{{ formatPrice(selectedTemplate.price) }}</strong><p class="service-description">{{ selectedTemplate.description || 'Brak opisu.' }}</p><div class="type-tags"><span v-for="type in selectedTemplate.deadline_types" :key="type" class="tag">{{ type }}</span></div></section>
        <p v-if="!editing" class="form-hint">Cena, opis i rodzaje terminów zostaną skopiowane z szablonu. Późniejsze zmiany szablonu nie zmienią tej usługi.</p>
      </fieldset>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <div class="service-page-actions"><button class="primary" :disabled="saving || !form.template_id || !form.company_id">{{ saving ? 'Zapisywanie…' : editing ? 'Zapisz zmiany' : 'Dodaj usługę' }}</button><button type="button" class="text-button" :disabled="saving" @click="visible = false; emit('cancelled')">Anuluj</button></div>
    </form>
</template>
