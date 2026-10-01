<script setup>
import { ref } from 'vue'
const props = defineProps({ request: Function, required: Boolean })
const emit = defineEmits(['changed'])
const current = ref(''), password = ref(''), repeat = ref(''), error = ref(''), busy = ref(false)
async function save() {
  error.value = ''
  if (password.value !== repeat.value) { error.value = 'Nowe hasła muszą być identyczne.'; return }
  busy.value = true
  try {
    await props.request('/auth/password', { method: 'POST', body: JSON.stringify({ current_password: current.value, new_password: password.value }) })
    current.value = ''; password.value = ''; repeat.value = ''; emit('changed')
  } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
</script>
<template>
  <form class="entry-form" @submit.prevent="save">
    <h2>Zmień hasło</h2>
    <p v-if="required">Przed rozpoczęciem pracy zmień hasło tymczasowe otrzymane e-mailem.</p>
    <div class="grid">
      <label>Obecne hasło<input v-model="current" type="password" autocomplete="current-password" required :disabled="busy" /></label>
      <label>Nowe hasło<input v-model="password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required :disabled="busy" /><small>Co najmniej 12 znaków.</small></label>
      <label>Powtórz nowe hasło<input v-model="repeat" type="password" autocomplete="new-password" minlength="12" maxlength="128" required :disabled="busy" /></label>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <button class="primary" :disabled="busy">{{ busy ? 'Zapisywanie…' : 'Zmień hasło' }}</button>
    <p>Po zmianie hasła zaloguj się ponownie. Poprzednie sesje zostaną zakończone.</p>
  </form>
</template>
