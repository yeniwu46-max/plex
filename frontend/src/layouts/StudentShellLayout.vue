<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import DashboardShell from '../components/layout/DashboardShell.vue'
import { useStudentNotificationSync } from '../composables/useStudentNotificationSync'
import { useStudentShellChrome } from '../composables/useStudentShellChrome'

defineOptions({ name: 'StudentShellLayout' })

useStudentNotificationSync()

const route = useRoute()
const chrome = useStudentShellChrome()
const pageKey = computed(() => {
  if (route.name === 'student-trial-practice') {
    return `${String(route.name)}:${String(route.params.questionId || '')}`
  }
  return String(route.name || route.path)
})

if (typeof window !== 'undefined') {
  window.setTimeout(() => {
    void import('../views/DiscoveryCabinView.vue').catch(() => undefined)
    void import('../views/StudentTrialView.vue').catch(() => undefined)
    void import('../views/StarPathLabView.vue').catch(() => undefined)
  }, 1200)
}
</script>

<template>
  <DashboardShell
    layout-host
    :active-nav="chrome.activeNav"
    :page-title="chrome.pageTitle"
    :page-subtitle="chrome.pageSubtitle"
    :search-placeholder="chrome.searchPlaceholder"
    :hide-search="chrome.hideSearch"
    :show-view-switcher="chrome.showViewSwitcher"
  >
    <router-view v-slot="{ Component }">
      <!-- KeepAlive 始终挂载，避免进出练习页时整表缓存被销毁 -->
      <keep-alive :max="8" :exclude="['StudentTrialPracticeView']">
        <component :is="Component" :key="pageKey" />
      </keep-alive>
    </router-view>
  </DashboardShell>
</template>
