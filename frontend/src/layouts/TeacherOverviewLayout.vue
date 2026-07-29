<script setup lang="ts">
import { computed, onMounted, provide } from 'vue'
import { useRoute } from 'vue-router'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import { TEACHER_OVERVIEW_KEY, useTeacherOverview } from '../composables/useTeacherOverview'
import { useTeacherNotificationSync } from '../composables/useTeacherNotificationSync'
import { useTeacherShellChrome } from '../composables/useTeacherShellChrome'

defineOptions({ name: 'TeacherOverviewLayout' })

const overview = useTeacherOverview()
provide(TEACHER_OVERVIEW_KEY, overview)
useTeacherNotificationSync()

const route = useRoute()
const chrome = useTeacherShellChrome()
const pageKey = computed(() => String(route.name || route.path))

onMounted(() => {
  void overview.loadOverview()
})
</script>

<template>
  <TeacherDashboardShell
    layout-host
    :active-nav="chrome.activeNav"
    :page-title="chrome.pageTitle"
    :page-subtitle="chrome.pageSubtitle"
    :search-placeholder="chrome.searchPlaceholder"
    :hide-search="chrome.hideSearch"
    :hide-toolbar="chrome.hideToolbar"
    :show-view-switcher="chrome.showViewSwitcher"
    :toolbar-label="chrome.toolbarLabel"
    :show-period="chrome.showPeriod"
    :show-activity="chrome.showActivity"
    :show-refresh="chrome.showRefresh"
  >
    <router-view v-slot="{ Component }">
      <!-- KeepAlive 始终挂载，避免进出出题页时整表缓存被销毁 -->
      <keep-alive :max="6" :exclude="['TeacherTrialCreateView']">
        <component :is="Component" :key="pageKey" />
      </keep-alive>
    </router-view>
  </TeacherDashboardShell>
</template>
