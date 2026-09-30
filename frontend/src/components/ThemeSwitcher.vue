<script setup>
import { theme, themes, setTheme } from '../theme.js'
import { Sun, Candy, Ghost, Smile } from 'lucide-vue-next'
const icons = { basic: Sun, sweet: Candy, dark: Ghost, colorful: Smile }
</script>

<template>
  <div class="theme-switcher" role="group" aria-label="Zmień wygląd">
    <div class="theme-options">
      <button v-for="item in themes" :key="item.id" type="button" class="theme-option" :class="{ selected: theme === item.id }" :aria-label="item.name" :aria-pressed="theme === item.id" :title="item.name + ' — ' + item.hint" @click="setTheme(item.id)">
        <component :is="icons[item.id]" :size="16" class="theme-character" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>
