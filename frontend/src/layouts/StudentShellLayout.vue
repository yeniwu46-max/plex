<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import DashboardShell from '../components/layout/DashboardShell.vue'
import StudentSectionTabs from '../components/student/StudentSectionTabs.vue'
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

/** 分区导航只在壳层渲染一次，避免 KeepAlive 多页 Teleport 叠出两行 tabs */
const sectionTabsArea = computed<'learning' | 'me' | null>(() => {
  const path = route.path
  if (path.startsWith('/student/star-path')) return 'learning'
  if (path.startsWith('/student/me')) return 'me'
  return null
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
    <template v-if="sectionTabsArea" #toolbar>
      <StudentSectionTabs :area="sectionTabsArea" />
    </template>
    <router-view v-slot="{ Component }">
      <!-- KeepAlive 始终挂载，避免进出练习页时整表缓存被销毁 -->
      <keep-alive :max="8" :exclude="['StudentTrialPracticeView']">
        <component :is="Component" :key="pageKey" />
      </keep-alive>
    </router-view>
  </DashboardShell>
</template>
