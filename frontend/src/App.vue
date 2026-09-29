<script setup>
  import { computed, onMounted, ref } from 'vue'
  import { Building2, CalendarDays, FileText, Inbox, LogOut, Plus, Search, ShieldCheck, X } from 'lucide-vue-next'

  const api = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
  const token = ref(localStorage.getItem('tms_token') || '')
  const active = ref('Firmy')
  const error = ref('')
  const email = ref('admin@tms.local')
  const password = ref('Admin123!')
  const companies = ref([])
  const documents = ref([])
  const deadlines = ref([])
  const emails = ref([])
  const showForm = ref(false)
  const company = ref({ kind: 'firma', name: '', nip: '', regon: '', pesel: '', email: '', phone: '' })
  const documentForm = ref({ company_id: '', title: '', number: '', status: 'nowy', due_date: '' })
  const deadline = ref({ title: '', due_date: '', status: 'planowany', notes: '', company_id: '' })
  const mailbox = ref({ host: '', username: '', password: '' })

  const navigation = [
    ['Firmy', Building2], ['Dokumenty', FileText], ['Terminarz', CalendarDays], ['Wiadomości', Inbox]
  ]
  const formTitle = computed(() => `Dodaj: ${active.value.slice(0, -1)}`)

  async function request(path, options = {}) {
    const response = await fetch(`${api}${path}`, { ...options, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token.value}`, ...options.headers } })
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Nie udało się wykonać operacji.')
    return response.json()
  }
  async function load() {
    if (!token.value) return
    try {
      ;[companies.value, documents.value, deadlines.value, emails.value] = await Promise.all([request('/companies'), request('/documents'), request('/deadlines'), request('/emails')])
    } catch (cause) { logout(); error.value = cause.message }
  }
  async function login() {
    error.value = ''
    try {
      const result = await fetch(`${api}/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: email.value, password: password.value }) })
      if (!result.ok) throw new Error('Nieprawidłowy e-mail lub hasło.')
      token.value = (await result.json()).access_token
      localStorage.setItem('tms_token', token.value)
      await load()
    } catch (cause) { error.value = cause.message }
  }
  function logout() { token.value = ''; localStorage.removeItem('tms_token') }
  async function submit() {
    const paths = { Firmy: ['/companies', company.value], Dokumenty: ['/documents', documentForm.value], Terminarz: ['/deadlines', deadline.value] }
    const [path, data] = paths[active.value]
    try { await request(path, { method: 'POST', body: JSON.stringify(data) }); showForm.value = false; await load() } catch (cause) { error.value = cause.message }
  }
  async function syncMail() {
    try { await request('/emails/sync', { method: 'POST', body: JSON.stringify(mailbox.value) }); await load() } catch (cause) { error.value = cause.message }
  }
  onMounted(load)
  </script>

  <template>
    <main v-if="!token" class="login-shell">
      <section class="login-card"><div class="brand"><ShieldCheck :size="31" /><span>TMS</span></div><p>Panel operacyjny</p>
        <form @submit.prevent="login"><label>E-mail<input v-model="email" type="email" /></label><label>Hasło<input v-model="password" type="password" /></label><button>Zaloguj się</button></form><small v-if="error" class="error">{{ error }}</small>
      </section>
    </main>
    <main v-else class="app-shell">
      <aside><div class="brand"><ShieldCheck :size="26" /><span>TMS</span></div><nav><button v-for="[item, icon] in navigation" :key="item" :class="{ selected: active === item }" @click="active = item; showForm = false"><component :is="icon" :size="19" />{{ item }}</button></nav><button class="logout" @click="logout"><LogOut :size="18" />Wyloguj</button></aside>
      <section class="content"><header><div><p class="eyebrow">Operacje</p><h1>{{ active }}</h1></div><button class="primary" @click="showForm = !showForm"><Plus v-if="!showForm" :size="18" /><X v-else :size="18" />{{ showForm ? 'Zamknij' : active === 'Wiadomości' ? 'Odbierz' : 'Dodaj' }}</button></header>
        <p v-if="error" class="error">{{ error }}</p>
      <div v-if="showForm" class="modal-backdrop" @click.self="showForm = false"><form v-if="active === 'Firmy'" class="entry-form modal" @submit.prevent="submit"><div class="modal-title"><h2>{{ formTitle }}</h2><button type="button" class="icon-button" aria-label="Zamknij" @click="showForm = false"><X :size="18" /></button></div><div class="grid"><label>Typ<select v-model="company.kind"><option value="firma">Firma</option><option value="osoba">Osoba</option></select></label><label>Nazwa<input v-model="company.name" required /></label><label>NIP<input v-model="company.nip" /></label><label>REGON<input v-model="company.regon" /></label><label>PESEL<input v-model="company.pesel" maxlength="11" /></label><label>E-mail<input v-model="company.email" type="email" /></label></div><button class="primary">Zapisz firmę</button></form>
        <form v-else-if="active === 'Dokumenty'" class="entry-form modal" @submit.prevent="submit"><div class="modal-title"><h2>{{ formTitle }}</h2><button type="button" class="icon-button" aria-label="Zamknij" @click="showForm = false"><X :size="18" /></button></div><div class="grid"><label>Firma<select v-model="documentForm.company_id" required><option disabled value="">Wybierz firmę</option><option v-for="item in companies" :value="item.id">{{ item.name }}</option></select></label><label>Nazwa<input v-model="documentForm.title" required /></label><label>Numer<input v-model="documentForm.number" /></label><label>Termin<input v-model="documentForm.due_date" type="date" /></label></div><button class="primary">Zapisz dokument</button></form>
        <form v-else-if="active === 'Terminarz'" class="entry-form modal" @submit.prevent="submit"><div class="modal-title"><h2>{{ formTitle }}</h2><button type="button" class="icon-button" aria-label="Zamknij" @click="showForm = false"><X :size="18" /></button></div><div class="grid"><label>Nazwa<input v-model="deadline.title" required /></label><label>Data<input v-model="deadline.due_date" type="date" required /></label><label>Firma<select v-model="deadline.company_id"><option value="">Bez firmy</option><option v-for="item in companies" :value="item.id">{{ item.name }}</option></select></label></div><button class="primary">Dodaj termin</button></form>
        <form v-else class="entry-form modal" @submit.prevent="syncMail"><div class="modal-title"><h2>Odbierz wiadomości</h2><button type="button" class="icon-button" aria-label="Zamknij" @click="showForm = false"><X :size="18" /></button></div><div class="grid"><label>Serwer IMAP<input v-model="mailbox.host" placeholder="imap.example.com" required /></label><label>Użytkownik<input v-model="mailbox.username" required /></label><label>Hasło aplikacji<input v-model="mailbox.password" type="password" required /></label></div><button class="primary">Synchronizuj IMAP</button></form></div>
        <section v-if="active === 'Firmy'" class="table"><div class="table-head"><Search :size="18" /><span>Nazwa</span><span>Typ</span><span>NIP / REGON</span></div><div v-for="item in companies" :key="item.id" class="row"><strong>{{ item.name }}</strong><span class="tag">{{ item.kind }}</span><span>{{ item.nip || '-' }} / {{ item.regon || '-' }}</span></div><p v-if="!companies.length" class="empty">Brak dodanych firm.</p></section>
        <section v-if="active === 'Dokumenty'" class="table"><div class="table-head"><span>Nazwa</span><span>Numer</span><span>Status</span><span>Termin</span></div><div v-for="item in documents" :key="item.id" class="row"><strong>{{ item.title }}</strong><span>{{ item.number || '-' }}</span><span class="tag">{{ item.status }}</span><span>{{ item.due_date || '-' }}</span></div><p v-if="!documents.length" class="empty">Brak dokumentów.</p></section>
        <section v-if="active === 'Terminarz'" class="calendar"><article v-for="item in deadlines" :key="item.id"><time>{{ item.due_date }}</time><strong>{{ item.title }}</strong><span class="tag">{{ item.status }}</span></article><p v-if="!deadlines.length" class="empty">Brak nadchodzących terminów.</p></section>
        <section v-if="active === 'Wiadomości'" class="mail"><article v-for="item in emails" :key="item.id"><strong>{{ item.subject }}</strong><span>{{ item.sender }}</span><p>{{ item.preview }}</p></article><p v-if="!emails.length" class="empty">Skrzynka nie została jeszcze zsynchronizowana.</p></section>
      </section>
    </main>
  </template>
