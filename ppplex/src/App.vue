<script setup lang="ts">
import DefenseNav from './components/DefenseNav.vue'
</script>

<template>
  <div class="app-shell">
    <DefenseNav />
    <div class="main-area">
      <RouterView />
    </div>
  </div>
</template>
