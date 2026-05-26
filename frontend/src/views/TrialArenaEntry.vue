<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import StudentTrialView from './StudentTrialView.vue'
import TrialArenaView from './TrialArenaView.vue'

const auth = useAuthStore()
const isTeacherSide = computed(() => {
  const role = auth.profile?.role
  return role === 'teacher' || role === 'admin'
})
</script>

<template>
  <TrialArenaView v-if="isTeacherSide" />
  <StudentTrialView v-else />
</template>
