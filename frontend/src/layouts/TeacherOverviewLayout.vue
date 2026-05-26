<script setup lang="ts">
import { onMounted, provide } from 'vue'
import { TEACHER_OVERVIEW_KEY, useTeacherOverview } from '../composables/useTeacherOverview'

const overview = useTeacherOverview()
provide(TEACHER_OVERVIEW_KEY, overview)

onMounted(() => {
  void overview.loadOverview()
})
</script>

<template>
  <router-view />
</template>
