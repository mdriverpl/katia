<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({ modelValue: String, options: Array, id: String, label: String, required: { type: Boolean, default: true }, maxlength: { type: Number, default: 100 }, placeholder: { type: String, default: 'Wpisz lub wybierz…' }, emptyMessage: { type: String, default: 'Brak podpowiedzi — możesz wpisać własną nazwę.' } })
const emit = defineEmits(['update:modelValue', 'selected'])
const expanded = ref(false)
const active = ref(-1)
const matches = computed(() => props.options.filter(item => item.name.toLocaleLowerCase('pl-PL').includes((props.modelValue || '').trim().toLocaleLowerCase('pl-PL'))))
watch(matches, () => { active.value = -1 })
function choose(item) {
  emit('update:modelValue', item.name)
  emit('selected', item)
  expanded.value = false
  active.value = -1
}
function move(direction) {
  expanded.value = true
  if (!matches.value.length) return
  active.value = (active.value + direction + matches.value.length) % matches.value.length
}
function enter(event) {
  if (!expanded.value) return
  event.preventDefault()
  if (active.value >= 0 && matches.value[active.value]) choose(matches.value[active.value])
}
</script>

<template>
  <div class="deadline-autocomplete">
    <label :for="id">{{ label }}</label>
    <input :id="id" :value="modelValue" role="combobox" aria-autocomplete="list" :aria-expanded="expanded" :aria-controls="id + '-options'" :aria-activedescendant="expanded && active >= 0 ? id + '-option-' + active : undefined" autocomplete="off" :placeholder="placeholder" :required="required" :maxlength="maxlength" @input="emit('update:modelValue', $event.target.value); expanded = true" @focus="expanded = true" @blur="expanded = false" @keydown.down.prevent="move(1)" @keydown.up.prevent="move(-1)" @keydown.enter="enter" @keydown.esc.stop.prevent="expanded = false" />
    <ul v-if="expanded" :id="id + '-options'" role="listbox" :aria-label="label" class="deadline-suggestions">
      <li v-for="(item, index) in matches" :id="id + '-option-' + index" :key="item.id" role="option" :aria-selected="active === index" :class="{ active: active === index }" @mousedown.prevent="choose(item)">
        <strong>{{ item.name }}</strong><small v-if="item.address || item.amount != null">{{ item.address }}<template v-if="item.amount != null"> · {{ new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(Number(item.amount)) }}</template></small>
      </li>
      <li v-if="!matches.length" role="presentation" class="suggestions-empty">{{ emptyMessage }}</li>
    </ul>
  </div>
</template>
