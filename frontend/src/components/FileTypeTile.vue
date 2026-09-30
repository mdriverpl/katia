<script setup>
import { computed } from 'vue'
import { FileText, Image } from 'lucide-vue-next'
const props = defineProps({ file: { type: Object, required: true } })
defineEmits(['preview'])
const kind = computed(() => {
  const extension = props.file.name.split('.').pop().toUpperCase()
  return extension === 'PDF' ? 'pdf' : ['JPG', 'JPEG', 'PNG', 'WEBP', 'GIF', 'HEIC', 'SVG', 'AVIF', 'BMP'].includes(extension) ? 'image' : ['DOC', 'DOCX', 'ODT'].includes(extension) ? 'document' : 'other'
})
</script>

<template>
  <button type="button" class="file-type-tile" :class="'file-type-' + kind" :title="file.name" :aria-label="'Podgląd ' + file.name" @click="$emit('preview')">
    <svg v-if="kind === 'pdf'" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M14 2H5v20h14V7l-5-5Z M14 2v6h5" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" /><rect x="1" y="11" width="22" height="9" rx="2" fill="currentColor" /><text x="12" y="17.8" text-anchor="middle" fill="white" font-size="7" font-weight="700" font-family="Arial, sans-serif">PDF</text></svg>
    <Image v-else-if="kind === 'image'" :size="14" aria-hidden="true" />
    <FileText v-else :size="14" aria-hidden="true" />
  </button>
</template>
