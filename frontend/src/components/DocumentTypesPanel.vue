<script setup>
import { ref } from 'vue'
import { Pencil, Trash2, X } from 'lucide-vue-next'

const props = defineProps({ types: { type: Array, required: true }, request: { type: Function, required: true } })
const emit = defineEmits(['saved'])
const visible = ref(false)
const saving = ref(false)
const name = ref('')
const error = ref('')
const editing = ref(null)
const deleting = ref(null)
const deleteError = ref('')
function open(item = null) {
  editing.value = item?.id || null
  name.value = item?.name || ''
  error.value = ''
  visible.value = true
}
async function save(request) {
  if (saving.value) return
  if (!name.value.trim()) { error.value = 'Wpisz nazwę rodzaju dokumentu.'; return }
  saving.value = true
  error.value = ''
  try {
    await request(editing.value ? `/document-types/${editing.value}` : '/document-types', { method: editing.value ? 'PUT' : 'POST', body: JSON.stringify({ name: name.value.trim() }) })
    visible.value = false
    emit('saved')
  } catch (cause) { error.value = cause.message }
  finally { saving.value = false }
}
async function remove(item) {
  if (deleting.value || !window.confirm(`Usunąć rodzaj „${item.name}”? Dokumenty i pliki pozostaną, ale bez przypisanego rodzaju.`)) return
  deleting.value = item.id; deleteError.value = ''
  try { await props.request(`/document-types/${item.id}`, { method: 'DELETE' }); emit('saved') }
  catch (cause) { deleteError.value = cause.message }
  finally { deleting.value = null }
}
defineExpose({ open })
</script>

<template>
  <p v-if="deleteError" class="error" role="alert">{{ deleteError }}</p>
  <section class="table data-list document-types-list" aria-label="Rodzaje dokumentów">
    <table v-if="types.length">
      <thead><tr><th scope="col">Lp.</th><th scope="col">Nazwa rodzaju dokumentu</th><th scope="col">Akcje</th></tr></thead>
      <tbody><tr v-for="(type, index) in types" :key="type.id"><td>{{ index + 1 }}</td><td><strong>{{ type.name }}</strong></td><td><button class="text-button" :disabled="!!deleting" :aria-label="'Edytuj ' + type.name" @click="open(type)"><Pencil :size="14" />Edytuj</button><button class="text-button" :disabled="!!deleting" :aria-label="'Usuń ' + type.name" @click="remove(type)"><Trash2 :size="14" />{{ deleting === type.id ? 'Usuwanie…' : 'Usuń' }}</button></td></tr></tbody>
    </table>
    <p v-if="!types.length" class="empty">Brak rodzajów dokumentów. Kliknij „Dodaj”, aby utworzyć pierwszy.</p>
  </section>
  <div v-if="visible" class="modal-backdrop" @click.self="!saving && (visible = false)">
    <form class="entry-form modal" role="dialog" aria-modal="true" aria-labelledby="document-type-title" @submit.prevent="save(request)">
      <div class="modal-title"><h2 id="document-type-title">{{ editing ? 'Edytuj rodzaj dokumentu' : 'Dodaj rodzaj dokumentu' }}</h2><button type="button" class="icon-button" aria-label="Zamknij" :disabled="saving" @click="visible = false"><X :size="18" /></button></div>
      <label>Nazwa rodzaju dokumentu<input v-model="name" required maxlength="100" :disabled="saving" placeholder="np. Zaświadczenie o zatrudnieniu" /></label>
      <p class="form-hint">Nowy rodzaj będzie dostępny przy dodawaniu dokumentów każdego klienta.</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="primary" :disabled="saving">{{ saving ? 'Zapisywanie…' : 'Zapisz rodzaj dokumentu' }}</button>
    </form>
  </div>
</template>
