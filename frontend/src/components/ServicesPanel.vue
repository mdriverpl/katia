<script setup>
import { nextTick, ref } from 'vue'
import { ArrowLeft, Pencil, Plus, Trash2, X } from 'lucide-vue-next'
import DeadlineTypeAutocomplete from './DeadlineTypeAutocomplete.vue'

const props = defineProps({ services: { type: Array, required: true }, deadlineTypes: { type: Array, default: () => [] }, request: { type: Function, required: true } })
const emit = defineEmits(['saved'])
const visible = ref(false)
const saving = ref(false)
const error = ref('')
const editing = ref(null)
const deleting = ref(null)
const deleteError = ref('')
const form = ref({ name: '', price: '', description: '', deadline_types: [] })
const details = ref([])
const formHeading = ref(null)
const typeKey = value => value.trim().toLocaleLowerCase('pl-PL')
function fillType(index) {
  const selected = props.deadlineTypes.find(item => typeKey(item.name) === typeKey(form.value.deadline_types[index]))
  details.value[index] = { address: selected?.address || '', amount: selected?.amount ?? '' }
  if (selected) form.value.deadline_types[index] = selected.name
}
function addType() {
  form.value.deadline_types.push('')
  details.value.push({ address: '', amount: '' })
}
function removeType(index) {
  form.value.deadline_types.splice(index, 1)
  details.value.splice(index, 1)
}
const formatPrice = value => value == null ? 'Cena nieustalona' : new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(Number(value))

function open(service = null) {
  if (visible.value) return
  editing.value = service?.id || null
  form.value = { name: service?.name || '', price: service?.price ?? '', description: service?.description || '', deadline_types: [...(service?.deadline_types || [])] }
  details.value = form.value.deadline_types.map(kind => {
    const saved = service?.deadline_details?.find(item => item.kind === kind)
    const source = saved || props.deadlineTypes.find(item => typeKey(item.name) === typeKey(kind))
    return { address: source?.address || '', amount: source?.amount ?? '' }
  })
  error.value = ''
  visible.value = true
  nextTick(() => { formHeading.value?.focus(); formHeading.value?.scrollIntoView({ block: 'start' }) })
}
async function save() {
  if (saving.value) return
  const types = form.value.deadline_types.map(value => value.trim())
  if (types.some(value => !value) || new Set(types.map(value => value.toLocaleLowerCase('pl-PL'))).size !== types.length) {
    error.value = 'Podaj różne, niepuste nazwy rodzajów terminu.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    await props.request(editing.value ? `/service-types/${editing.value}` : '/service-types', {
      method: editing.value ? 'PUT' : 'POST',
      body: JSON.stringify({ ...form.value, name: form.value.name.trim(), price: form.value.price === '' ? null : String(form.value.price), deadline_types: types, deadline_details: types.map((kind, index) => ({ kind, address: details.value[index].address.trim() || null, amount: details.value[index].amount === '' ? null : String(details.value[index].amount) })) }),
    })
    visible.value = false
    emit('saved')
  } catch (cause) { error.value = cause.message }
  finally { saving.value = false }
}
async function remove(service) {
  if (deleting.value || !window.confirm(`Usunąć rodzaj usługi „${service.name}”? Dotychczasowe usługi klientów i terminy zostaną zachowane.`)) return
  deleting.value = service.id
  deleteError.value = ''
  try {
    await props.request(`/service-types/${service.id}`, { method: 'DELETE' })
    emit('saved')
  } catch (cause) { deleteError.value = cause.message }
  finally { deleting.value = null }
}

defineExpose({ open })
</script>

<template>
  <p v-if="deleteError" class="error" role="alert">{{ deleteError }}</p>
  <section v-if="!visible" class="data-list service-types-list" aria-label="Rodzaje usług">
    <table v-if="services.length">
      <thead><tr><th scope="col">Rodzaj usługi / opis</th><th scope="col">Cena</th><th scope="col">Rodzaje terminu</th><th scope="col">Akcje</th></tr></thead>
      <tbody><tr v-for="service in services" :key="service.id">
        <td><strong>{{ service.name }}</strong><p v-if="service.description" class="service-list-description">{{ service.description }}</p></td>
        <td>{{ formatPrice(service.price) }}</td>
        <td><div v-if="service.deadline_types.length" class="type-tags"><span v-for="type in service.deadline_types" :key="type" class="tag">{{ type }}</span></div><span v-else class="form-hint">Brak rodzajów terminu</span></td>
        <td><div class="client-actions"><button class="text-button" :disabled="!!deleting" :aria-label="'Edytuj rodzaj usługi ' + service.name" @click="open(service)"><Pencil :size="15" />Edytuj</button><button class="text-button" :disabled="!!deleting" :aria-label="'Usuń rodzaj usługi ' + service.name" @click="remove(service)"><Trash2 :size="15" />{{ deleting === service.id ? 'Usuwanie…' : 'Usuń' }}</button></div></td>
      </tr></tbody>
    </table>
    <p v-if="!services.length" class="empty">Brak rodzajów usług. Dodaj pierwszy szablon.</p>
  </section>
    <form v-else class="entry-form compact-service-form service-template-form service-template-page" aria-labelledby="service-form-title" @submit.prevent="save">
      <button type="button" class="text-button" :disabled="saving" @click="visible = false"><ArrowLeft :size="16" />Wróć do listy</button>
      <div class="modal-title"><h2 id="service-form-title" ref="formHeading" tabindex="-1">{{ editing ? 'Edytuj rodzaj usługi' : 'Dodaj rodzaj usługi' }}</h2></div>
      <fieldset class="service-fields" :disabled="saving">
        <label>Nazwa rodzaju usługi<input v-model="form.name" required maxlength="255" placeholder="np. KOD95" /></label>
        <label>Cena (PLN)<input v-model="form.price" type="number" min="0" max="9999999999.99" step="0.01" placeholder="Nieustalona" /></label>
        <label class="service-description-field">Opis<textarea v-model="form.description" rows="2" placeholder="Co obejmuje usługa?" /></label>
        <div class="service-heading"><h3>Rodzaje terminów</h3><button type="button" class="text-button" :disabled="form.deadline_types.length >= 30" @click="addType"><Plus :size="16" />Dodaj rodzaj</button></div>
        <p class="form-hint">Wpisz nazwę i wybierz podpowiedź. Adres i kwota uzupełnią się automatycznie — możesz je zmienić dla tego szablonu.</p>
        <div v-for="(_, index) in form.deadline_types" :key="index" class="template-term-row">
          <DeadlineTypeAutocomplete :id="'template-kind-' + index" :label="'Rodzaj ' + (index + 1)" :model-value="form.deadline_types[index]" :options="deadlineTypes" @update:model-value="form.deadline_types[index] = $event; fillType(index)" />
          <label>Adres<input v-model="details[index].address" maxlength="2000" placeholder="Adres terminu" /></label>
          <label>Kwota (PLN)<input v-model="details[index].amount" type="number" min="0" max="9999999999.99" step="0.01" placeholder="Nieustalona" /></label>
          <button type="button" class="icon-button" :aria-label="'Usuń rodzaj ' + (index + 1)" @click="removeType(index)"><X :size="16" /></button>
        </div>
      </fieldset>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <div class="service-page-actions"><button class="primary" :disabled="saving">{{ saving ? 'Zapisywanie…' : 'Zapisz szablon' }}</button><button type="button" class="text-button" :disabled="saving" @click="visible = false">Anuluj</button></div>
    </form>
</template>
