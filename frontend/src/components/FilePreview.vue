<script setup>
import { nextTick, onBeforeUnmount, ref } from 'vue'
import { Download, X } from 'lucide-vue-next'

const props = defineProps({ request: Function })
const dialog = ref(null)
const file = ref(null)
const url = ref('')
const mime = ref('')
const loading = ref(false)
const error = ref('')
let version = 0
function release() {
  version++
  if (url.value) URL.revokeObjectURL(url.value)
  url.value = ''
}
function close() { dialog.value?.close(); release() }
async function open(documentId, attachment) {
  release()
  const current = version
  file.value = attachment
  error.value = ''; loading.value = true
  const extension = attachment.name.split('.').pop().toLowerCase()
  mime.value = ({ pdf: 'application/pdf', jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', gif: 'image/gif', webp: 'image/webp', avif: 'image/avif', bmp: 'image/bmp', svg: 'image/svg+xml' })[extension] || ''
  await nextTick()
  if (current !== version) return
  if (!dialog.value.open) dialog.value.showModal()
  try {
    const blob = await props.request(`/documents/${documentId}/files/${attachment.id}`, { download: true })
    if (current !== version) return
    // The API deliberately sends octet-stream. Use a restricted preview MIME type.
    url.value = URL.createObjectURL(new Blob([blob], { type: mime.value || 'application/octet-stream' }))
  } catch (cause) { if (current === version) error.value = cause.message }
  finally { if (current === version) loading.value = false }
}
onBeforeUnmount(release)
defineExpose({ open })
</script>

<template>
  <dialog ref="dialog" class="file-preview" aria-labelledby="file-preview-title" @close="release" @click=" $event.target === dialog && close()">
    <div class="file-preview-shell">
      <header class="file-preview-header"><h2 id="file-preview-title">{{ file?.name }}</h2><div><a v-if="url" class="text-button" :href="url" :download="file?.name"><Download :size="16" />Pobierz</a><button type="button" class="icon-button" aria-label="Zamknij podgląd" autofocus @click="close"><X :size="20" /></button></div></header>
      <div class="file-preview-body" :aria-busy="loading">
        <p v-if="loading" role="status">Wczytywanie podglądu…</p>
        <p v-else-if="error" class="error" role="alert">{{ error }}</p>
        <template v-else-if="url">
          <img v-if="mime.startsWith('image/')" :src="url" :alt="file.name" @error="error = 'Nie można wyświetlić tego obrazu. Pobierz plik, aby go otworzyć.'" />
          <object v-else-if="mime === 'application/pdf'" :data="url" type="application/pdf" :aria-label="'Podgląd PDF: ' + file.name"><p>Przeglądarka nie obsługuje podglądu PDF. Użyj przycisku „Pobierz”.</p></object>
          <p v-else>Podgląd tego formatu nie jest dostępny. Użyj przycisku „Pobierz”.</p>
        </template>
      </div>
      <p v-if="mime === 'application/pdf' && url" class="file-preview-note">Jeśli PDF nie jest widoczny, pobierz go i otwórz na urządzeniu.</p>
    </div>
  </dialog>
</template>
