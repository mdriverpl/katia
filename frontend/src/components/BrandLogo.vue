<script setup>
import BrandMark from './BrandMark.vue'
</script>
<template>
  <div class="brand space-flow-brand" aria-label="Space & Flow">
    <BrandMark class="space-flow-mark" />
    <span class="space-flow-wordmark">
      <span class="space-flow-title" role="img" aria-label="Space & Flow">
        <span class="space-flow-word space-flow-word-space" aria-hidden="true">Space</span>
        <span class="space-flow-amp" aria-hidden="true">&</span>
        <span class="space-flow-word space-flow-word-flow" aria-hidden="true">Flow</span>
      </span>
    </span>
  </div>
</template>
