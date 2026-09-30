<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import StatusBadge from './StatusBadge.vue'
import { dateKey } from '../calendar.js'
import { statusInfo } from '../status.js'
const props = defineProps({ deadlines: Array, clients: Array, services: Array, recent: Array })
defineEmits(['client', 'event', 'create'])
const today = ref(dateKey(new Date()))
const timer = setInterval(() => { today.value = dateKey(new Date()) }, 60000)
onBeforeUnmount(() => clearInterval(timer))
const todays = computed(() => props.deadlines.filter(item => item.due_date === today.value))
const overdue = computed(() => props.deadlines.filter(item => statusInfo(item.status, item.due_date, today.value).tone === 'overdue'))
const recentClients = computed(() => props.recent.map(id => props.clients.find(item => item.id === id)).filter(Boolean))
const running = computed(() => props.services.filter(item => item.progress > 0 && item.progress < 100).length)
const selected = ref('today')
const events = computed(() => selected.value === 'today' ? todays.value : overdue.value)
</script>
<template>
  <div class="today-actions"><button class="primary" @click="$emit('create', 'Klienci')">Dodaj klienta</button><button class="text-button" @click="$emit('create', 'Dokumenty')">Dodaj dokument</button><button class="text-button" @click="$emit('create', 'Usługi')">Dodaj usługę</button></div>
  <section class="metrics"><article><span>Terminy na dziś</span><strong>{{ todays.length }}</strong><small>{{ new Date(today + 'T12:00:00').toLocaleDateString('pl-PL') }}</small></article><article><span>Zaległe terminy</span><strong>{{ overdue.length }}</strong><small>Wymagają sprawdzenia</small></article><article><span>Usługi w trakcie</span><strong>{{ running }}</strong><small>Rozpoczęte i niezakończone</small></article></section>
  <div class="today-layout"><section class="today-card"><div class="client-related-tabs"><button :class="{ selected: selected === 'today' }" :aria-pressed="selected === 'today'" @click="selected = 'today'">Dzisiaj ({{ todays.length }})</button><button :class="{ selected: selected === 'overdue' }" :aria-pressed="selected === 'overdue'" @click="selected = 'overdue'">Zaległe ({{ overdue.length }})</button></div><div class="table data-list today-table"><table v-if="events.length"><thead><tr><th scope="col">Termin / klient</th><th scope="col">Data</th><th scope="col">Status</th></tr></thead><tbody><tr v-for="item in events" :key="item.id"><td><button class="text-button" @click="$emit('event', item)">{{ item.title }}</button><small>{{ clients.find(client => client.id === item.company_id)?.name || 'Bez klienta' }}</small></td><td>{{ new Date(item.due_date + 'T12:00:00').toLocaleDateString('pl-PL') }}<small>{{ item.scheduled_time }}</small></td><td><StatusBadge :status="item.status" :due-date="item.due_date" /></td></tr></tbody></table><p v-else class="empty">{{ selected === 'today' ? 'Brak terminów na dziś.' : 'Brak zaległych terminów.' }}</p></div></section><section class="today-card recent-clients"><h2>Ostatnio otwierani klienci</h2><button v-for="item in recentClients" :key="item.id" class="recent-client" @click="$emit('client', item)"><strong>{{ item.name }}</strong><span>Otwórz kartę →</span></button><p v-if="!recentClients.length" class="empty">Tutaj pojawią się otwierane przez Ciebie karty klientów.</p></section></div>
</template>
