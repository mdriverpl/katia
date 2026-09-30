<script setup>
import { computed, ref } from 'vue'
import { Search, X } from 'lucide-vue-next'
const props = defineProps({ clients: Array, disabled: Boolean })
const emit = defineEmits(['open'])
const query = ref('')
const visible = ref(false)
const results = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase('pl-PL')
  if (!needle) return []
  return props.clients.map(item => ({ kind: 'Klienci', item, name: item.name, detail: [item.phone, item.email].filter(Boolean).join(' · ') || 'Otwórz kartę klienta', search: `${item.name} ${item.first_name || ''} ${item.last_name || ''} ${item.phone || ''} ${item.email || ''}` }))
    .filter(item => item.search.toLocaleLowerCase('pl-PL').includes(needle)).slice(0, 20)
})
function choose(result) { emit('open', result); visible.value = false; query.value = '' }
function blur(event) { if (!event.currentTarget.contains(event.relatedTarget)) visible.value = false }
function move(event, direction) {
  const buttons = [...event.currentTarget.querySelectorAll('.global-search-result')]
  if (!buttons.length) return
  const index = buttons.indexOf(document.activeElement)
  buttons[(index + direction + buttons.length) % buttons.length].focus()
}
</script>
<template>
  <div class="global-search" @focusout="blur" @keydown.esc="visible = false" @keydown.down.prevent="move($event, 1)" @keydown.up.prevent="move($event, -1)">
    <label class="global-search-field"><input v-model="query" type="search" aria-label="Szukaj klienta" placeholder="Imię, nazwisko, nazwa, telefon lub e-mail…" :disabled="disabled" autocomplete="off" @input="visible = true" @focus="visible = true" @keydown.enter.prevent="results.length && choose(results[0])" /></label>
    <div v-if="visible && query.trim()" class="global-search-results"><p class="form-hint">{{ results.length ? 'Wyniki wyszukiwania (maks. 20)' : 'Brak pasujących wyników.' }}</p><button v-for="result in results" :key="result.kind + result.item.id" type="button" class="global-search-result" @click="choose(result)"><strong>{{ result.name }}</strong><small>{{ result.detail }}</small></button><button class="text-button" @click="visible = false"><X :size="14" />Zamknij</button></div>
    <div class="search-animation" aria-hidden="true"><span /><span /><span /><Search :size="64" :stroke-width="1.4" /></div>
  </div>
</template>
<style scoped>
.global-search-field input { padding-left: 14px; }
.search-animation { position: relative; display: flex; align-items: center; justify-content: center; width: 110px; height: 110px; margin: 48px auto 32px; color: var(--muted); pointer-events: none; }
.search-animation span { position: absolute; inset: 0; border: 1px solid currentColor; border-radius: 50%; opacity: 0; animation: search-ripple 6s ease-out infinite; }
.search-animation span:nth-child(2) { animation-delay: -2s; }
.search-animation span:nth-child(3) { animation-delay: -4s; }
.search-animation svg { animation: search-float 4s ease-in-out infinite; }
.global-search-results { transform-origin: top center; animation: search-reveal .18s ease-out; }
@keyframes search-float {
  0%, 100% { transform: translateY(4px) rotate(-8deg); }
  50% { transform: translateY(-6px) rotate(8deg); }
}
@keyframes search-ripple { from { transform: scale(.55); opacity: .3; } to { transform: scale(1.7); opacity: 0; } }
@keyframes search-reveal { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
@media (prefers-reduced-motion: reduce) {
  .search-animation svg, .search-animation span, .global-search-results { animation: none; }
}
</style>
