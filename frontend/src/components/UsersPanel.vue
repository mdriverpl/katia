<script setup>
import { onMounted, ref } from 'vue'
const props = defineProps({ request: Function, currentUserId: String })
const users = ref([])
const email = ref('')
const role = ref('employee')
const busy = ref(false)
const error = ref('')
const notice = ref('')
async function load() { users.value = await props.request('/users') }
async function run(action) {
  if (busy.value) return
  busy.value = true; error.value = ''; notice.value = ''
  try { await action(); await load() } catch (cause) { error.value = cause.message }
  finally { busy.value = false }
}
async function create() {
  await run(async () => {
    await props.request('/users', { method: 'POST', body: JSON.stringify({ email: email.value, role: role.value }) })
    email.value = ''; role.value = 'employee'; notice.value = 'Konto utworzone. Wiadomość z hasłem tymczasowym przekazano do wysyłki.'
  })
}
function update(user, changes) {
  return run(() => props.request(`/users/${user.id}`, { method: 'PUT', body: JSON.stringify({ role: user.role, blocked: user.blocked, ...changes }) }))
}
function remove(user) {
  if (confirm(`Usunąć konto ${user.email}? Tej operacji nie można cofnąć.`))
    return run(() => props.request(`/users/${user.id}`, { method: 'DELETE' }))
}
onMounted(() => run(async () => {}))
</script>

<template>
  <form class="entry-form" @submit.prevent="create">
    <h2>Dodaj użytkownika</h2>
    <div class="grid">
      <label>E-mail<input v-model="email" type="email" maxlength="255" required :disabled="busy" /></label>
      <label>Typ użytkownika<select v-model="role" :disabled="busy"><option value="employee">Pracownik</option><option value="admin">Admin</option></select></label>
    </div>
    <p>Użytkownik otrzyma hasło tymczasowe e-mailem. Przy pierwszym logowaniu ustawi własne hasło.</p>
    <button class="primary" :disabled="busy">{{ busy ? 'Zapisywanie…' : 'Utwórz konto i wyślij e-mail' }}</button>
  </form>
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <p v-if="notice" role="status">{{ notice }}</p>
  <section class="table data-list">
    <table><thead><tr><th>E-mail</th><th>Typ</th><th>Status</th><th>Akcje</th></tr></thead>
      <tbody><tr v-for="user in users" :key="user.id">
        <td>{{ user.email }}<small v-if="user.id === currentUserId">Twoje konto</small></td>
        <td><select :value="user.role" :disabled="busy || user.id === currentUserId" :aria-label="'Typ użytkownika ' + user.email" @change="update(user, { role: $event.target.value })"><option value="employee">Pracownik</option><option value="admin">Admin</option></select></td>
        <td>{{ user.blocked ? 'Zablokowany' : 'Aktywny' }}<small v-if="user.must_change_password">Wymagana zmiana hasła</small></td>
        <td><button class="text-button" :disabled="busy || user.id === currentUserId" @click="update(user, { blocked: !user.blocked })">{{ user.blocked ? 'Odblokuj' : 'Zablokuj' }}</button><button class="text-button" :disabled="busy || user.id === currentUserId" @click="remove(user)">Usuń</button></td>
      </tr></tbody>
    </table>
  </section>
</template>
