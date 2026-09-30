<script setup>
import { computed } from 'vue'
import { statusInfo } from '../status.js'
const props = defineProps({ status: String, dueDate: String, progress: Number })
const state = computed(() => statusInfo(props.progress == null ? props.status : props.progress >= 100 ? 'wykonany' : props.progress > 0 ? 'w trakcie' : 'planowany', props.dueDate))
</script>
<template><span class="status-badge" :class="'status-' + state.tone"><i aria-hidden="true" />{{ state.label }}</span></template>
