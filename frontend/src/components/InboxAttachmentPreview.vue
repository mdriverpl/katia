<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({ request: Function, messageId: String, file: Object })
defineEmits(['download'])
const url = ref(''), text = ref(''), mime = ref(''), loading = ref(false), error = ref('')
let generation = 0
function release() {
  generation++
  if (url.value) URL.revokeObjectURL(url.value)
  url.value = ''; text.value = ''; error.value = ''; loading.value = false
}
watch(() => [props.messageId, props.file?.id], async () => {
  release()
  mime.value = previewType(props.file?.name)
  if (!props.file || !props.messageId || !mime.value) return
  const current = generation
  loading.value = true
  try {
    const blob = await props.request(`/inbox/${props.messageId}/attachments/${props.file.id}`, { download: true })
    if (current !== generation) return
    if (mime.value === 'text/plain') {
      const value = await blob.slice(0, 512 * 1024).text()
      if (current !== generation) return
      text.value = value + (blob.size > 512 * 1024 ? '\n\n[Podgląd skrócony. Pobierz plik, aby przeczytać całość.]' : '')
    } else {
      url.value = URL.createObjectURL(new Blob([blob], { type: mime.value }))
    }
  } catch (cause) { if (current === generation) error.value = cause.message }
  finally { if (current === generation) loading.value = false }
}, { immediate: true })
onBeforeUnmount(release)
</script>

<script>
// Render only these formats; HTML and SVG attachments remain download-only.
export function previewType(name = '') {
  return ({ pdf: 'application/pdf', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', gif: 'image/gif', webp: 'image/webp', bmp: 'image/bmp', avif: 'image/avif', txt: 'text/plain', csv: 'text/plain', log: 'text/plain' })[name.split('.').pop().toLowerCase()] || ''
}
</script>

<template>
  <section v-if="file" class="attachment-preview" aria-label="Podgląd załącznika" :aria-busy="loading">
    <header><strong>{{ file.name }}</strong><a v-if="url" :href="url" :download="file.name" class="text-button">Pobierz</a><button v-else type="button" class="text-button" @click="$emit('download', file)">Pobierz</button></header>
    <div class="attachment-canvas">
      <p v-if="loading" role="status">Wczytywanie podglądu…</p>
      <p v-else-if="error" class="error" role="alert">{{ error }}</p>
      <img v-else-if="url && mime.startsWith('image/')" :key="url" :src="url" :alt="file.name" @error="error = 'Nie można wyświetlić obrazu. Pobierz plik, aby go otworzyć.'" />
      <object v-else-if="url && mime === 'application/pdf'" :key="url" :data="url" type="application/pdf" :aria-label="'Podgląd PDF: ' + file.name"><p>Podgląd PDF jest niedostępny w tej przeglądarce. Użyj przycisku „Pobierz”.</p></object>
      <pre v-else-if="mime === 'text/plain'">{{ text || '(pusty plik)' }}</pre>
      <p v-else>Ten format nie ma podglądu. Pobierz plik, aby go otworzyć.</p>
    </div>
    <small v-if="mime === 'application/pdf' && url">Jeśli PDF nie jest widoczny, użyj przycisku „Pobierz”.</small>
  </section>
</template>

<style scoped>
.attachment-preview{border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:16px 0}
.attachment-preview header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 14px;border-bottom:1px solid var(--line)}
.attachment-preview strong{overflow-wrap:anywhere;min-width:0}.attachment-preview .text-button{flex-shrink:0}
.attachment-canvas{min-height:160px;background:var(--theme-soft,#f1f3ef)}
.attachment-canvas>p{padding:20px}.attachment-canvas object{display:block;width:100%;height:65vh;min-height:350px;border:0}
.attachment-canvas img{display:block;max-width:100%;max-height:65vh;object-fit:contain;margin:auto}
.attachment-canvas pre{margin:0;padding:16px;white-space:pre-wrap;overflow-wrap:anywhere;max-height:65vh;overflow:auto}
.attachment-preview>small{display:block;padding:8px 14px;color:var(--muted)}
</style>
