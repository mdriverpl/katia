<script setup>
import { ref } from 'vue'
import { FileText, X } from 'lucide-vue-next'

defineProps({ types: { type: Array, required: true }, request: { type: Function, required: true } })
const emit = defineEmits(['saved'])
const visible = ref(false)
const saving = ref(false)
const name = ref('')
const error = ref('')
function open() {
  name.value = ''
  error.value = ''
  visible.value = true
}
async function save(request) {
  if (saving.value) return
  if (!name.value.trim()) { error.value = 'Wpisz nazwę rodzaju dokumentu.'; return }
  saving.value = true
  error.value = ''
  try {
    await request('/document-types', { method: 'POST', body: JSON.stringify({ name: name.value.trim() }) })
    visible.value = false
    emit('saved')
  } catch (cause) { error.value = cause.message }
  finally { saving.value = false }
}
defineExpose({ open })
</script>

<template>
  <section class="document-types-list">
    <article v-for="type in types" :key="type.id" class="document-type-card"><FileText :size="20" /><span>{{ type.name }}</span></article>
    <p v-if="!types.length" class="empty">Brak rodzajów dokumentów. Kliknij „Dodaj”, aby utworzyć pierwszy.</p>
  </section>
  <div v-if="visible" class="modal-backdrop" @click.self="!saving && (visible = false)">
    <form class="entry-form modal" role="dialog" aria-modal="true" aria-labelledby="document-type-title" @submit.prevent="save(request)">
      <div class="modal-title"><h2 id="document-type-title">Dodaj rodzaj dokumentu</h2><button type="button" class="icon-button" aria-label="Zamknij" :disabled="saving" @click="visible = false"><X :size="18" /></button></div>
      <label>Nazwa rodzaju dokumentu<input v-model="name" required maxlength="100" :disabled="saving" placeholder="np. Zaświadczenie o zatrudnieniu" /></label>
      <p class="form-hint">Nowy rodzaj będzie dostępny przy dodawaniu dokumentów każdego klienta.</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="primary" :disabled="saving">{{ saving ? 'Zapisywanie…' : 'Zapisz rodzaj dokumentu' }}</button>
    </form>
  </div>
</template>
