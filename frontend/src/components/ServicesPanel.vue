<script setup>
import { ref } from 'vue'
import { Pencil, Plus, X } from 'lucide-vue-next'

const props = defineProps({ services: { type: Array, required: true }, request: { type: Function, required: true } })
const emit = defineEmits(['saved'])
const visible = ref(false)
const saving = ref(false)
const error = ref('')
const editing = ref(null)
const form = ref({ name: '', price: '', description: '', deadline_types: [] })
const formatPrice = value => value == null ? 'Cena nieustalona' : new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(Number(value))

function open(service = null) {
  editing.value = service?.id || null
  form.value = { name: service?.name || '', price: service?.price ?? '', description: service?.description || '', deadline_types: [...(service?.deadline_types || [])] }
  error.value = ''
  visible.value = true
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
      body: JSON.stringify({ ...form.value, name: form.value.name.trim(), price: form.value.price === '' ? null : String(form.value.price), deadline_types: types }),
    })
    visible.value = false
    emit('saved')
  } catch (cause) { error.value = cause.message }
  finally { saving.value = false }
}
defineExpose({ open })
</script>

<template>
  <section class="services-grid">
    <article v-for="service in services" :key="service.id" class="service-card">
      <div class="service-heading"><h2>{{ service.name }}</h2><button class="text-button" :aria-label="'Edytuj rodzaj usługi ' + service.name" @click="open(service)"><Pencil :size="15" />Edytuj</button></div>
      <strong class="service-price">{{ formatPrice(service.price) }}</strong>
      <p class="service-description">{{ service.description || 'Dodaj opis szablonu podczas edycji.' }}</p>
      <p class="eyebrow">Rodzaje terminu</p>
      <div v-if="service.deadline_types.length" class="type-tags"><span v-for="type in service.deadline_types" :key="type" class="tag">{{ type }}</span></div>
      <p v-else class="form-hint">Brak rodzajów — dodaj je podczas edycji szablonu.</p>
    </article>
    <p v-if="!services.length" class="empty">Brak rodzajów usług. Dodaj pierwszy szablon.</p>
  </section>
  <div v-if="visible" class="modal-backdrop" @click.self="!saving && (visible = false)">
    <form class="entry-form modal" role="dialog" aria-modal="true" aria-labelledby="service-form-title" @submit.prevent="save">
      <div class="modal-title"><h2 id="service-form-title">{{ editing ? 'Edytuj rodzaj usługi' : 'Dodaj rodzaj usługi' }}</h2><button type="button" class="icon-button" aria-label="Zamknij" :disabled="saving" @click="visible = false"><X :size="18" /></button></div>
      <fieldset class="service-fields" :disabled="saving">
        <label>Nazwa rodzaju usługi<input v-model="form.name" required maxlength="255" placeholder="np. KOD95" /></label>
        <label>Cena (PLN)<input v-model="form.price" type="number" min="0" max="9999999999.99" step="0.01" placeholder="Nieustalona" /></label>
        <label>Opis<textarea v-model="form.description" rows="4" placeholder="Co obejmuje usługa?" /></label>
        <div class="service-heading"><h3>Rodzaje terminu</h3><button type="button" class="text-button" :disabled="form.deadline_types.length >= 30" @click="form.deadline_types.push('')"><Plus :size="16" />Dodaj rodzaj</button></div>
        <p class="form-hint">Możesz dodać kilka rodzajów, np. szkolenie, badania lub egzamin. Będą dostępne w terminarzu po wybraniu tego rodzaju usługi.</p>
        <div v-for="(_, index) in form.deadline_types" :key="index" class="type-editor"><label :for="'deadline-type-' + index">Rodzaj {{ index + 1 }}</label><input :id="'deadline-type-' + index" v-model="form.deadline_types[index]" required maxlength="100" /><button type="button" class="icon-button" :aria-label="'Usuń rodzaj ' + (index + 1)" @click="form.deadline_types.splice(index, 1)"><X :size="16" /></button></div>
      </fieldset>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="primary" :disabled="saving">{{ saving ? 'Zapisywanie…' : 'Zapisz szablon' }}</button>
    </form>
  </div>
</template>
