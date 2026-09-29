<script setup>
  import { computed, onMounted, ref } from 'vue'
  import { ArrowUpRight, Building2, CalendarDays, ChevronLeft, ChevronRight, FileText, Inbox, LogOut, Pencil, Plus, ShieldCheck, BriefcaseBusiness, X } from 'lucide-vue-next'
  import ServicesPanel from './components/ServicesPanel.vue'
  import ClientServicesPanel from './components/ClientServicesPanel.vue'
  import DocumentTypesPanel from './components/DocumentTypesPanel.vue'

  import { api } from './api.js'
  import { dateKey, monthDays } from './calendar.js'


  const token = ref(localStorage.getItem('tms_token') || '')
  const active = ref('Klienci')
  const error = ref('')
  const email = ref('admin@tms.local')
  const password = ref('Admin123!')
  const companies = ref([])
  const documents = ref([])
  const documentTypes = ref([])
  const documentTypesPanel = ref(null)
  const documentClientFilter = ref('')
  const visibleDocuments = computed(() => documents.value.filter(item => !documentClientFilter.value || item.company_id === documentClientFilter.value))
  const deadlines = ref([])
  const emails = ref([])
  const services = ref([])
  const servicePanel = ref(null)
  const clientServices = ref([])
  const clientServicePanel = ref(null)
  const showForm = ref(false)
  const contactTypes = { email: 'E-mail', phone: 'Telefon', whatsapp: 'WhatsApp', viber: 'Viber', telegram: 'Telegram' }
  const editingCompany = ref(null)
  const busy = ref(false)
  const selectedFiles = ref([])
  const savedDocumentId = ref(null)
  const attachmentDocument = ref(null)
  const calendarMonth = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))
  const selectedDay = ref(dateKey(new Date()))
  const monthLabel = computed(() => calendarMonth.value.toLocaleDateString('pl-PL', { month: 'long', year: 'numeric' }))
  const calendarDays = computed(() => monthDays(calendarMonth.value))
  const eventsByDay = computed(() => {
    const result = {}
    for (const event of deadlines.value) (result[event.due_date] ||= []).push(event)
    return result
  })
  const dayEvents = computed(() => eventsByDay.value[selectedDay.value] || [])
  const company = ref({ kind: 'firma', name: '', nip: '', regon: '', pesel: '', first_name: '', last_name: '', phone: '', email: '', country: '', language: '', contact_type: null, residential_address: '', birth_date: '', passport_number: '', employer_name: '', employer_email: '', employer_phone: '' })
  const documentForm = ref({ company_id: '', title: '', number: '', status: 'nowy', due_date: '', document_type_id: null })
  const deadline = ref({ title: '', due_date: '', status: 'planowany', notes: '', company_id: '', service_id: null, deadline_types: [] })
  const availableDeadlineTypes = computed(() => services.value.find(service => service.id === deadline.value.service_id)?.deadline_types || [])
  const mailbox = ref({ host: '', username: '', password: '' })

  const navigation = [
    ['Klienci', Building2], ['Usługi', BriefcaseBusiness], ['Rodzaje usług', FileText], ['Dokumenty', FileText], ['Rodzaje dokumentów', FileText], ['Terminarz', CalendarDays], ['Wiadomości', Inbox]
  ]
  const formTitle = computed(() => editingCompany.value && active.value === 'Klienci' ? 'Edytuj klienta' : ({ Klienci: 'Dodaj klienta', Dokumenty: 'Dodaj dokument', Terminarz: 'Dodaj termin' })[active.value])
  const pageDescription = computed(() => ({ Klienci: 'Dobre relacje zaczynają się od porządku w kontaktach.', Usługi: 'Usługi przypisane do Twoich klientów.', 'Rodzaje usług': 'Szablony usług: cena, opis i rodzaje terminów.', Dokumenty: 'Wszystkie ważne dokumenty pod ręką.', 'Rodzaje dokumentów': 'Lista rodzajów dokumentów i własne pozycje.', Terminarz: 'Zaplanuj kolejne kroki i zadbaj o terminy.', Wiadomości: 'Twoja korespondencja w centrum wydarzeń.' })[active.value])

  async function request(path, options = {}) {
    const response = await fetch(`${api}${path}`, { ...options, headers: { ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), Authorization: `Bearer ${token.value}`, ...options.headers } })
    if (!response.ok) {
      if (response.status === 401) logout()
      const detail = (await response.json().catch(() => ({}))).detail
      throw new Error(typeof detail === 'string' ? detail : 'Sprawdź poprawność wprowadzonych danych.')
    }
    if (options.download) return response.blob()
    return response.json()
  }
  async function load() {
    if (!token.value) return
    try {
      ;[companies.value, documents.value, deadlines.value, emails.value, services.value, clientServices.value, documentTypes.value] = await Promise.all([request('/companies'), request('/documents'), request('/deadlines'), request('/emails'), request('/service-types'), request('/client-services'), request('/document-types')])
    } catch (cause) { error.value = cause.message }
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
  function logout() { token.value = ''; localStorage.removeItem('tms_token'); showForm.value = false; attachmentDocument.value = null }
  function openForm() {
    if (active.value === 'Rodzaje dokumentów') { documentTypesPanel.value?.open(); return }
    if (active.value === 'Rodzaje usług') { servicePanel.value?.open(); return }
    if (active.value === 'Usługi') { clientServicePanel.value?.open(); return }
    if (showForm.value) { showForm.value = false; return }
    error.value = ''
    editingCompany.value = null
    company.value = { kind: 'firma', name: '', nip: '', regon: '', pesel: '', first_name: '', last_name: '', phone: '', email: '', country: '', language: '', contact_type: null, residential_address: '', birth_date: '', passport_number: '', employer_name: '', employer_email: '', employer_phone: '' }
    documentForm.value = { company_id: documentClientFilter.value, title: '', number: '', status: 'nowy', due_date: '', document_type_id: null }
    deadline.value = { title: '', due_date: selectedDay.value, status: 'planowany', notes: '', company_id: '', service_id: null, deadline_types: [] }
    selectedFiles.value = []
    savedDocumentId.value = null
    showForm.value = true
  }
  async function editCompany(item) {
    if (busy.value) return
    busy.value = true
    error.value = ''
    try {
      const details = await request(`/companies/${item.id}`)
      editingCompany.value = item.id
      company.value = { ...details, pesel: details.pesel || '' }
      showForm.value = true
    } catch (cause) { error.value = cause.message }
    finally { busy.value = false }
  }
  function openClientDocuments(item) {
    active.value = 'Dokumenty'
    documentClientFilter.value = item.id
    showForm.value = false
    error.value = ''
  }
  function changeMonth(offset) {
    calendarMonth.value = new Date(calendarMonth.value.getFullYear(), calendarMonth.value.getMonth() + offset, 1)
    selectedDay.value = dateKey(calendarMonth.value)
  }
  function goToday() {
    const today = new Date()
    calendarMonth.value = new Date(today.getFullYear(), today.getMonth(), 1)
    selectedDay.value = dateKey(today)
  }
  function chooseFiles(event) {
    const files = Array.from(event.target.files)
    if (files.length > 10 || files.some(file => file.size > 20 * 1024 * 1024)) {
      error.value = 'Wybierz maksymalnie 10 plików, każdy do 20 MB.'
      event.target.value = ''
      selectedFiles.value = []
      return
    }
    error.value = ''
    selectedFiles.value = files
  }
  async function uploadFiles(id) {
    if (!selectedFiles.value.length) return
    const body = new FormData()
    selectedFiles.value.forEach(file => body.append('files', file))
    await request(`/documents/${id}/files`, { method: 'POST', body })
    selectedFiles.value = []
  }
  function openAttachments(document) {
    attachmentDocument.value = document
    selectedFiles.value = []
    error.value = ''
  }
  async function saveAttachments() {
    if (busy.value) return
    busy.value = true
    error.value = ''
    try { await uploadFiles(attachmentDocument.value.id); attachmentDocument.value = null; await load() }
    catch (cause) { error.value = cause.message }
    finally { busy.value = false }
  }
  async function downloadFile(documentId, file) {
    try {
      const blob = await request(`/documents/${documentId}/files/${file.id}`, { download: true })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url; link.download = file.name; link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (cause) { error.value = cause.message }
  }
  async function submit() {
    if (busy.value) return
    busy.value = true
    error.value = ''
    try {
      if (active.value === 'Klienci') {
        const data = { ...company.value, birth_date: company.value.birth_date || null, passport_number: company.value.passport_number?.trim() || null }
        if (editingCompany.value && !data.pesel) delete data.pesel
        await request(editingCompany.value ? `/companies/${editingCompany.value}` : '/companies', { method: editingCompany.value ? 'PUT' : 'POST', body: JSON.stringify(data) })
      } else if (active.value === 'Dokumenty') {
        if (!savedDocumentId.value) {
          const result = await request('/documents', { method: 'POST', body: JSON.stringify({ ...documentForm.value, due_date: documentForm.value.due_date || null }) })
          savedDocumentId.value = result.id
        }
        await uploadFiles(savedDocumentId.value)
      } else {
        await request('/deadlines', { method: 'POST', body: JSON.stringify({ ...deadline.value, company_id: deadline.value.company_id || null }) })
      }
      showForm.value = false
      await load()
    } catch (cause) { error.value = savedDocumentId.value && active.value === 'Dokumenty' ? `Dokument zapisano. Nie udało się dodać plików: ${cause.message} Ponów zapis, aby wysłać pliki.` : cause.message }
    finally { busy.value = false }
  }
  async function syncMail() {
    try { await request('/emails/sync', { method: 'POST', body: JSON.stringify(mailbox.value) }); await load() } catch (cause) { error.value = cause.message }
  }
  onMounted(load)
  </script>

  <template>
    <main v-if="!token" class="login-shell">
      <section class="login-story">
        <div class="brand"><ShieldCheck :size="31" /><span>TMS<span class="brand-caption">WORKSPACE</span></span></div>
        <div class="story-copy"><p class="eyebrow">MNIEJ CHAOSU. WIĘCEJ PRZESTRZENI.</p><h1>Twój biznes.<br />W dobrym<br /><em>porządku.</em></h1><p>Klienci, dokumenty i codzienne sprawy.<br />Jedno miejsce, w którym wszystko się łączy.</p><div class="story-modules"><span><Building2 :size="16" />Relacje</span><span><FileText :size="16" />Dokumenty</span><span><CalendarDays :size="16" />Plany</span></div></div>
        <span class="story-footer">TMS / CENTRUM OPERACYJNE</span>
      </section>
      <section class="login-card"><p class="eyebrow">TWOJA PRZESTRZEŃ DO PRACY</p><h2>Dobrze Cię widzieć.</h2><p>Zaloguj się i uporządkuj swój dzień.</p>
        <form @submit.prevent="login"><label>E-mail<input v-model="email" type="email" autocomplete="username" required /></label><label>Hasło<input v-model="password" type="password" autocomplete="current-password" required /></label><button>Zaloguj się <ArrowUpRight :size="18" /></button></form><small v-if="error" class="error" role="alert">{{ error }}</small><div class="login-note"><ShieldCheck :size="17" /><span>Twoje centrum codziennych spraw.</span></div>
      </section>
    </main>
    <main v-else class="app-shell">
      <aside><div class="brand"><ShieldCheck :size="26" /><span>TMS</span></div><p class="workspace-label">CENTRUM OPERACYJNE</p><nav><button v-for="[item, icon] in navigation" :key="item" :class="{ selected: active === item }" :disabled="busy" @click="active = item; showForm = false; error = ''"><component :is="icon" :size="19" />{{ item }}</button></nav><button class="logout" :disabled="busy" @click="logout"><LogOut :size="18" />Wyloguj</button></aside>
      <section class="content"><header class="page-header"><div><p class="eyebrow">TMS / Centrum operacyjne</p><h1>{{ active }}</h1><p class="page-description">{{ pageDescription }}</p></div><div class="header-actions"><span class="system-status"><i></i>System online</span><button class="primary" :disabled="busy" @click="openForm"><Plus v-if="!showForm" :size="18" /><X v-else :size="18" />{{ showForm ? 'Zamknij' : active === 'Wiadomości' ? 'Odbierz' : 'Dodaj' }}</button></div></header>
        <p v-if="error" class="error">{{ error }}</p><DocumentTypesPanel v-if="active === 'Rodzaje dokumentów'" ref="documentTypesPanel" :types="documentTypes" :request="request" @saved="load" /><ServicesPanel v-if="active === 'Rodzaje usług'" ref="servicePanel" :services="services" :request="request" @saved="load" /><ClientServicesPanel v-if="active === 'Usługi'" ref="clientServicePanel" :services="clientServices" :templates="services" :clients="companies" :request="request" @saved="load" />
        <section v-if="active === 'Klienci'" class="metrics"><article><span>Wszyscy klienci</span><strong>{{ companies.length }}</strong><small>Klienci w bazie</small></article><article><span>Dokumenty</span><strong>{{ documents.length }}</strong><small>Pozycje wymagające obsługi</small></article><article><span>Terminy</span><strong>{{ deadlines.length }}</strong><small>W harmonogramie</small></article></section>
      <div v-if="showForm" class="modal-backdrop" @click.self="!busy && (showForm = false)"><form v-if="active === 'Klienci'" class="entry-form modal" @submit.prevent="submit"><div class="modal-title"><h2>{{ formTitle }}</h2><button type="button" class="icon-button" aria-label="Zamknij" :disabled="busy" @click="showForm = false"><X :size="18" /></button></div><div class="grid"><label>Typ klienta<select v-model="company.kind"><option value="firma">Firma</option><option value="osoba">Osoba</option></select></label><label>Nazwa<input v-model="company.name" required /></label><label>Imię<input v-model="company.first_name" /></label><label>Nazwisko<input v-model="company.last_name" /></label><label>Data urodzenia<input v-model="company.birth_date" type="date" :max="dateKey(new Date())" autocomplete="bday" /></label><label>Seria i numer paszportu<input v-model="company.passport_number" maxlength="100" autocomplete="off" /></label><label>Telefon<input v-model="company.phone" type="tel" /></label><label>E-mail<input v-model="company.email" type="email" /></label><label>Rodzaj kontaktu<select v-model="company.contact_type"><option :value="null">Nie wybrano</option><option v-for="(label, value) in contactTypes" :key="value" :value="value">{{ label }}</option></select></label><label class="address-field">Adres zamieszkania<input v-model="company.residential_address" autocomplete="street-address" placeholder="Ulica, nr domu / lokalu, kod pocztowy, miejscowość, kraj" /></label><label>Kraj pochodzenia<input v-model="company.country" /></label><label>Język<input v-model="company.language" /></label><label>NIP<input v-model="company.nip" /></label><label>REGON<input v-model="company.regon" /></label><label>PESEL<input v-model="company.pesel" maxlength="11" :placeholder="editingCompany ? 'Puste = bez zmian' : ''" /></label></div><fieldset class="employer-fields"><legend>Dane pracodawcy</legend><div class="grid"><label>Nazwa pracodawcy<input v-model="company.employer_name" maxlength="255" autocomplete="section-employer organization" /></label><label>E-mail pracodawcy<input v-model="company.employer_email" type="email" maxlength="255" autocomplete="section-employer email" /></label><label>Telefon pracodawcy<input v-model="company.employer_phone" type="tel" maxlength="50" autocomplete="section-employer tel" /></label></div></fieldset><p v-if="error" class="error" role="alert">{{ error }}</p><button class="primary" :disabled="busy">{{ busy ? 'Zapisywanie…' : 'Zapisz klienta' }}</button></form>
        <form v-else-if="active === 'Dokumenty'" class="entry-form modal" @submit.prevent="submit"><div class="modal-title"><h2>{{ formTitle }}</h2><button type="button" class="icon-button" aria-label="Zamknij" :disabled="busy" @click="showForm = false"><X :size="18" /></button></div><fieldset class="grid" :disabled="busy || !!savedDocumentId"><label>Klient<select v-model="documentForm.company_id" required><option disabled value="">Wybierz klienta</option><option v-for="item in companies" :value="item.id">{{ item.name }}</option></select></label><label>Rodzaj dokumentu<select v-model="documentForm.document_type_id"><option :value="null">Nie wybrano</option><option v-for="type in documentTypes" :key="type.id" :value="type.id">{{ type.name }}</option></select></label><label>Nazwa<input v-model="documentForm.title" required /></label><label>Numer<input v-model="documentForm.number" /></label><label>Termin<input v-model="documentForm.due_date" type="date" /></label></fieldset><p class="form-hint">Dokument z datą automatycznie pojawi się w terminarzu.</p><label>Załączniki<input type="file" multiple :disabled="busy" @change="chooseFiles" /><small>Do 10 plików jednocześnie, maks. 20 MB każdy.</small></label><ul v-if="selectedFiles.length" class="file-list"><li v-for="file in selectedFiles" :key="file.name">{{ file.name }}</li></ul><p v-if="error" class="error" role="alert">{{ error }}</p><button class="primary" :disabled="busy">{{ busy ? 'Zapisywanie…' : savedDocumentId ? 'Ponów wysyłanie plików' : 'Zapisz dokument' }}</button></form>
        <form v-else-if="active === 'Terminarz'" class="entry-form modal" @submit.prevent="submit"><div class="modal-title"><h2>{{ formTitle }}</h2><button type="button" class="icon-button" aria-label="Zamknij" :disabled="busy" @click="showForm = false"><X :size="18" /></button></div><div class="grid"><label>Nazwa<input v-model="deadline.title" required /></label><label>Data<input v-model="deadline.due_date" type="date" required /></label><label>Rodzaj usługi<select v-model="deadline.service_id" @change="deadline.deadline_types = []"><option :value="null">Bez rodzaju usługi</option><option v-for="service in services" :key="service.id" :value="service.id">{{ service.name }}</option></select></label><fieldset v-if="availableDeadlineTypes.length" class="deadline-type-options"><legend>Rodzaje terminu — wybierz jeden lub kilka</legend><label v-for="type in availableDeadlineTypes" :key="type"><input v-model="deadline.deadline_types" type="checkbox" :value="type" />{{ type }}</label></fieldset><label>Klient<select v-model="deadline.company_id"><option value="">Bez klienta</option><option v-for="item in companies" :value="item.id">{{ item.name }}</option></select></label></div><p v-if="error" class="error" role="alert">{{ error }}</p><button class="primary" :disabled="busy">{{ busy ? 'Zapisywanie…' : 'Dodaj termin' }}</button></form>
        <form v-else class="entry-form modal" @submit.prevent="syncMail"><div class="modal-title"><h2>Odbierz wiadomości</h2><button type="button" class="icon-button" aria-label="Zamknij" :disabled="busy" @click="showForm = false"><X :size="18" /></button></div><div class="grid"><label>Serwer IMAP<input v-model="mailbox.host" placeholder="imap.example.com" required /></label><label>Użytkownik<input v-model="mailbox.username" required /></label><label>Hasło aplikacji<input v-model="mailbox.password" type="password" required /></label></div><button class="primary">Synchronizuj IMAP</button></form></div>
        <section v-if="active === 'Klienci'" class="table company-table"><div class="table-head"><span>Nazwa / kontakt</span><span>Typ</span><span>Kraj / język</span><span>NIP / REGON</span><span>Akcje</span></div><div v-for="item in companies" :key="item.id" class="row"><span><strong>{{ item.name }}</strong><small>{{ [item.first_name, item.last_name].filter(Boolean).join(' ') || item.email || item.phone || '-' }}</small><small>Rodzaj kontaktu: {{ contactTypes[item.contact_type] || 'Nie wybrano' }}</small><small v-if="item.residential_address">Adres: {{ item.residential_address }}</small></span><span class="tag">{{ item.kind }}</span><span>{{ item.country || '-' }} / {{ item.language || '-' }}</span><span>{{ item.nip || '-' }} / {{ item.regon || '-' }}</span><div class="client-actions"><button class="text-button" :disabled="busy" :aria-label="'Edytuj klienta ' + item.name" @click="editCompany(item)"><Pencil :size="14" />Edytuj</button><button class="text-button" :disabled="busy" :aria-label="'Dokumenty klienta ' + item.name" @click="openClientDocuments(item)"><FileText :size="14" />Dokumenty</button></div></div><p v-if="!companies.length" class="empty">Brak dodanych klientów.</p></section>
        <div v-if="active === 'Dokumenty'" class="document-filter"><label>Dokumenty klienta<select v-model="documentClientFilter"><option value="">Wszyscy klienci</option><option v-for="item in companies" :key="item.id" :value="item.id">{{ item.name }}</option></select></label><span class="form-hint">Dokumentów: {{ visibleDocuments.length }}</span></div><section v-if="active === 'Dokumenty'" class="table"><div class="table-head"><span>Nazwa</span><span>Numer</span><span>Status</span><span>Termin</span></div><div v-for="item in visibleDocuments" :key="item.id" class="row"><div><strong>{{ item.title }}</strong><small>Rodzaj: {{ documentTypes.find(type => type.id === item.document_type_id)?.name || 'Nie wybrano' }}</small><small>{{ companies.find(company => company.id === item.company_id)?.name }}</small><div class="document-files"><button v-for="file in item.files" :key="file.id" class="file-link" @click="downloadFile(item.id, file)"><FileText :size="13" />{{ file.name }}</button><button class="text-button" @click="openAttachments(item)"><Plus :size="13" />Dodaj pliki</button></div></div><span>{{ item.number || '-' }}</span><span class="tag">{{ item.status }}</span><span>{{ item.due_date || '-' }}</span></div><p v-if="!visibleDocuments.length" class="empty">Brak dokumentów. Kliknij „Dodaj”, aby dodać dokument z plikami.</p></section>
        <section v-if="active === 'Terminarz'" class="calendar-panel">
          <div class="calendar-toolbar"><h2>{{ monthLabel }}</h2><div class="calendar-controls"><button class="text-button" @click="goToday">Dzisiaj</button><button class="icon-button" aria-label="Poprzedni miesiąc" @click="changeMonth(-1)"><ChevronLeft :size="18" /></button><button class="icon-button" aria-label="Następny miesiąc" @click="changeMonth(1)"><ChevronRight :size="18" /></button></div></div>
          <div class="month-grid"><div v-for="day in ['Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Nd']" :key="day" class="weekday">{{ day }}</div><button v-for="day in calendarDays" :key="day.key" class="calendar-day" :class="{ outside: day.outside, today: day.key === dateKey(new Date()), chosen: day.key === selectedDay }" :aria-label="day.key + ', terminów: ' + (eventsByDay[day.key] || []).length" :aria-pressed="day.key === selectedDay" @click="selectedDay = day.key"><span class="day-number">{{ day.number }}</span><span v-for="event in (eventsByDay[day.key] || []).slice(0, 2)" :key="event.id" class="calendar-event" :class="{ 'document-event': event.document_id }">{{ event.title }}</span><span v-if="(eventsByDay[day.key] || []).length > 2" class="more-events">+{{ eventsByDay[day.key].length - 2 }} więcej</span><span v-if="eventsByDay[day.key]?.length" class="mobile-event-count">{{ eventsByDay[day.key].length }} term.</span></button></div>
          <div class="calendar-legend"><span><i></i>Termin własny</span><span><i class="document-dot"></i>Dokument</span></div>
          <section class="day-agenda" aria-live="polite"><div class="calendar-toolbar"><h2>{{ new Date(selectedDay + 'T12:00:00').toLocaleDateString('pl-PL', { day: 'numeric', month: 'long', year: 'numeric' }) }}</h2><button class="text-button" @click="openForm"><Plus :size="16" />Dodaj termin</button></div><article v-for="event in dayEvents" :key="event.id" class="agenda-event"><div><strong>{{ event.title }}</strong><small v-if="event.scheduled_time">Godzina: {{ event.scheduled_time }}</small><small v-if="event.cost != null">Koszt: {{ new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(Number(event.cost)) }}</small><small>{{ event.document_id ? 'Dokument' : 'Termin własny' }}<template v-if="event.company_id"> · {{ companies.find(company => company.id === event.company_id)?.name }}</template></small><small v-if="event.service_id">Rodzaj usługi: {{ services.find(service => service.id === event.service_id)?.name }}</small><div v-if="event.deadline_types?.length" class="type-tags"><span v-for="type in event.deadline_types" :key="type" class="tag">{{ type }}</span></div><p v-if="event.notes">{{ event.notes }}</p></div><span class="tag">{{ event.status }}</span></article><p v-if="!dayEvents.length" class="empty">Brak terminów na ten dzień.</p></section>
        </section>
        <div v-if="attachmentDocument" class="modal-backdrop" @click.self="!busy && (attachmentDocument = null)"><form class="entry-form modal" @submit.prevent="saveAttachments"><div class="modal-title"><h2>Pliki: {{ attachmentDocument.title }}</h2><button type="button" class="icon-button" aria-label="Zamknij" :disabled="busy" @click="attachmentDocument = null"><X :size="18" /></button></div><label>Wybierz pliki<input type="file" multiple required :disabled="busy" @change="chooseFiles" /><small>Do 10 plików jednocześnie, maks. 20 MB każdy.</small></label><ul v-if="selectedFiles.length" class="file-list"><li v-for="file in selectedFiles" :key="file.name">{{ file.name }}</li></ul><p v-if="error" class="error" role="alert">{{ error }}</p><button class="primary" :disabled="busy || !selectedFiles.length">{{ busy ? 'Wysyłanie…' : 'Dodaj pliki' }}</button></form></div>
        <section v-if="active === 'Wiadomości'" class="mail"><article v-for="item in emails" :key="item.id"><strong>{{ item.subject }}</strong><span>{{ item.sender }}</span><p>{{ item.preview }}</p></article><p v-if="!emails.length" class="empty">Skrzynka nie została jeszcze zsynchronizowana.</p></section>
      </section>
    </main>
  </template>
