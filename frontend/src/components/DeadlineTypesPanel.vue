<script setup>
import { ref } from 'vue'
import { Pencil, X } from 'lucide-vue-next'

const props = defineProps({ types: Array, request: Function })
const emit = defineEmits(['saved'])
const visible = ref(false)
const saving = ref(false)
const editing = ref(null)
const error = ref('')
const form = ref({})
const formatAmount = value => value == null ? 'Nieustalona' : new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(Number(value))
function open(item = null) {
  editing.value = item?.id || null
  form.value = { name: item?.name || '', client_calendar: item?.client_calendar ?? true, operator_calendar: item?.operator_calendar ?? true, address: item?.address || '', amount: item?.amount ?? '' }
  error.value = ''
  visible.value = true
}
async function save() {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    await props.request(editing.value ? `/deadline-types/${editing.value}` : '/deadline-types', { method: editing.value ? 'PUT' : 'POST', body: JSON.stringify({ ...form.value, amount: form.value.amount === '' ? null : String(form.value.amount) }) })
    visible.value = false
    emit('saved')
  } catch (cause) { error.value = cause.message }
  finally { saving.value = false }
}
defineExpose({ open })
</script>

<template>
  <section class="data-list deadline-types-list" aria-label="Rodzaje terminów">
    <table v-if="types.length">
      <thead><tr><th scope="col">Nazwa</th><th scope="col">Kalendarz klienta</th><th scope="col">Kalendarz operatora</th><th scope="col">Adres</th><th scope="col">Kwota</th><th scope="col">Akcje</th></tr></thead>
      <tbody><tr v-for="item in types" :key="item.id">
        <td><strong>{{ item.name }}</strong></td>
        <td><input type="checkbox" :checked="item.client_calendar" disabled :aria-label="'Kalendarz klienta: ' + item.name" /></td>
        <td><input type="checkbox" :checked="item.operator_calendar" disabled :aria-label="'Kalendarz operatora: ' + item.name" /></td>
        <td>{{ item.address || '—' }}</td>
        <td>{{ formatAmount(item.amount) }}</td>
        <td><button class="text-button" :aria-label="'Edytuj rodzaj terminu ' + item.name" @click="open(item)"><Pencil :size="15" />Edytuj</button></td>
      </tr></tbody>
    </table>
    <p v-else class="empty">Brak rodzajów terminów. Kliknij „Dodaj”, aby utworzyć pierwszy.</p>
  </section>
  <div v-if="visible" class="modal-backdrop" @click.self="!saving && (visible = false)">
    <form class="entry-form modal deadline-type-form" role="dialog" aria-modal="true" aria-labelledby="deadline-type-title" @submit.prevent="save">
      <div class="modal-title"><h2 id="deadline-type-title">{{ editing ? 'Edytuj rodzaj terminu' : 'Dodaj rodzaj terminu' }}</h2><button type="button" class="icon-button" aria-label="Zamknij" :disabled="saving" @click="visible = false"><X :size="18" /></button></div>
      <fieldset class="service-fields" :disabled="saving">
        <label>Nazwa<input v-model="form.name" required maxlength="100" /></label>
        <label>Kwota (PLN)<input v-model="form.amount" type="number" min="0" max="9999999999.99" step="0.01" placeholder="Nieustalona" /></label>
        <div class="calendar-visibility-options">
          <label class="calendar-visibility-option"><input v-model="form.client_calendar" type="checkbox" /><span>Kalendarz klienta</span></label>
          <label class="calendar-visibility-option"><input v-model="form.operator_calendar" type="checkbox" /><span>Kalendarz operatora</span></label>
        </div>
        <label>Adres<textarea v-model="form.address" rows="2" maxlength="2000" placeholder="Ulica, numer, kod pocztowy, miejscowość" /></label>
        <p class="form-hint">Zaznaczenie określa widoczność tego rodzaju terminu w terminarzu klienta i operatora. Ustawienia dotyczą również istniejących terminów.</p>
      </fieldset>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="primary" :disabled="saving">{{ saving ? 'Zapisywanie…' : 'Zapisz' }}</button>
    </form>
  </div>
</template>
