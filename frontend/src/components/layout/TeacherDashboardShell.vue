<script setup lang="ts">
import { inject, onMounted, provide, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon } from 'naive-ui'
import { MapOutline } from '@vicons/ionicons5'
import TeacherSidebar, { type TeacherNavKey } from './TeacherSidebar.vue'
import PlexTopbar from './PlexTopbar.vue'
import TeacherToolbar from '../teacher/TeacherToolbar.vue'
import {
  TEACHER_OVERVIEW_KEY,
  TEACHER_SHELL_SEARCH_KEY,
  useTeacherOverview,
} from '../../composables/useTeacherOverview'
import { applyTeacherShellChrome } from '../../composables/useTeacherShellChrome'

const TEACHER_SHELL_NESTED = 'plex-teacher-shell-nested'
const TOOLBAR_FILTERS_ID = 'plex-teacher-shell-toolbar-filters'
const TOOLBAR_TRAILING_ID = 'plex-teacher-shell-toolbar-trailing'

const props = withDefaults(
  defineProps<{
    activeNav: TeacherNavKey
    pageTitle: string
    pageSubtitle?: string
    searchPlaceholder?: string
    showViewSwitcher?: boolean
    hideSearch?: boolean
    hideToolbar?: boolean
    toolbarLabel?: string
    showPeriod?: boolean
    showActivity?: boolean
    showRefresh?: boolean
    layoutHost?: boolean
  }>(),
  {
    pageSubtitle: '观察整个知识宇宙的成长轨迹',
    searchPlaceholder: '搜索班级、学生…',
    showViewSwitcher: false,
    hideSearch: false,
    hideToolbar: false,
    toolbarLabel: '教师端筛选与状态',
    showPeriod: false,
    showActivity: true,
    showRefresh: true,
    layoutHost: false,
  },
)

defineEmits<{
  viewSwitch: [key: string]
}>()

const router = useRouter()
const nested = inject(TEACHER_SHELL_NESTED, false)
const isHost = props.layoutHost || !nested
const contentOnly = !isHost

if (isHost) {
  provide(TEACHER_SHELL_NESTED, true)
}

const parentOverview = inject(TEACHER_OVERVIEW_KEY, null)
const overview = parentOverview ?? useTeacherOverview()
if (!parentOverview) {
  provide(TEACHER_OVERVIEW_KEY, overview)
}

const sidebarCollapsed = ref(false)
const searchText = ref('')
provide(TEACHER_SHELL_SEARCH_KEY, searchText)

watchEffect(() => {
  if (contentOnly) {
    applyTeacherShellChrome({
      activeNav: props.activeNav,
      pageTitle: props.pageTitle,
      pageSubtitle: props.pageSubtitle || '观察整个知识宇宙的成长轨迹',
      searchPlaceholder: props.searchPlaceholder || '搜索班级、学生…',
      hideSearch: props.hideSearch,
      hideToolbar: props.hideToolbar,
      showViewSwitcher: props.showViewSwitcher,
      toolbarLabel: props.toolbarLabel || '教师端筛选与状态',
      showPeriod: props.showPeriod,
      showActivity: props.showActivity,
      showRefresh: props.showRefresh,
    })
  }
})

function goStarMap() {
  void router.push('/teacher/starfield')
}

onMounted(() => {
  if (isHost && !parentOverview) {
    void overview.loadOverview()
  }
})
</script>

<template>
  <div v-if="isHost" class="shell teacher-shell" :class="{ 'shell--collapsed': sidebarCollapsed }">
    <TeacherSidebar v-model:collapsed="sidebarCollapsed" :active-key="activeNav" />

    <div class="main teacher-main">
      <header class="teacher-header">
        <PlexTopbar
          v-model:search="searchText"
          :title="pageTitle"
          :subtitle="pageSubtitle"
          :placeholder="searchPlaceholder"
          :hide-search="hideSearch"
        />

        <div v-if="showViewSwitcher" class="topbar-actions">
          <n-button secondary round size="small" class="view-switch" @click="goStarMap">
            <n-icon :component="MapOutline" :size="18" />
            <span class="view-switch__text">查看星图</span>
          </n-button>
        </div>

        <div v-if="!hideToolbar" class="toolbar-slot">
          <TeacherToolbar
            :aria-label="toolbarLabel"
            :show-period="showPeriod"
            :show-activity="showActivity"
            :show-refresh="showRefresh"
          >
            <template #filters>
              <div :id="TOOLBAR_FILTERS_ID" />
              <slot name="toolbar-filters" />
            </template>
            <template #trailing>
              <div :id="TOOLBAR_TRAILING_ID" />
              <slot name="toolbar-trailing" />
            </template>
          </TeacherToolbar>
        </div>
        <!-- 即使隐藏工具栏也保留传送目标，避免子页 Teleport 报错 -->
        <template v-else>
          <div :id="TOOLBAR_FILTERS_ID" class="toolbar-teleport-anchor" />
          <div :id="TOOLBAR_TRAILING_ID" class="toolbar-teleport-anchor" />
        </template>
      </header>

      <div class="main-body">
        <slot />
      </div>
    </div>
  </div>

  <template v-else>
    <Teleport defer :to="`#${TOOLBAR_FILTERS_ID}`">
      <slot name="toolbar-filters" />
    </Teleport>
    <Teleport defer :to="`#${TOOLBAR_TRAILING_ID}`">
      <slot name="toolbar-trailing" />
    </Teleport>
    <slot />
  </template>
</template>

<style scoped>
.shell {
  display: flex;
  height: 100%;
  min-height: 100%;
  max-height: 100%;
  overflow: hidden;
  background: #050a0e;
  color: #e2e8f0;
  font-family: 'Outfit', 'Noto Sans SC', system-ui, sans-serif;
}

.shell :deep(.teacher-sidebar) {
  position: sticky;
  top: 0;
  align-self: stretch;
  height: 100%;
  max-height: 100%;
  flex-shrink: 0;
}

.teacher-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(ellipse 80% 50% at 50% -10%, rgba(251, 146, 60, 0.08), transparent),
    radial-gradient(ellipse 60% 40% at 90% 60%, rgba(251, 191, 36, 0.05), transparent),
    linear-gradient(180deg, #050a0e 0%, #030712 55%, #020617 100%);
}

.teacher-main::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.28;
  background-image:
    radial-gradient(1px 1px at 10% 20%, rgba(255, 200, 120, 0.25), transparent),
    radial-gradient(1px 1px at 80% 40%, rgba(255, 255, 255, 0.12), transparent);
  background-size: 320px 320px;
}

.teacher-header {
  position: relative;
  z-index: 2;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding-bottom: 0.35rem;
}

.teacher-header :deep(.plex-topbar) {
  padding-bottom: 0;
}

.toolbar-slot {
  width: 100%;
  padding-inline: var(--plex-page-gutter-x);
  box-sizing: border-box;
}

.toolbar-teleport-anchor {
  display: none;
}

.main-body {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}

.topbar-actions {
  position: relative;
  z-index: 2;
  padding: 0 1.25rem;
}

.view-switch {
  display: inline-flex !important;
  align-items: center;
  gap: 0.4rem;
  border: 1px solid rgba(251, 146, 60, 0.2) !important;
  background: rgba(15, 23, 42, 0.55) !important;
  color: #fff7ed !important;
}

@media (max-width: 900px) {
  .teacher-header :deep(.plex-topbar--compact) {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .teacher-header :deep(.plex-topbar--compact .plex-topbar__userbar) {
    grid-column: 1;
    grid-row: 2;
    justify-self: start;
  }
}

@media (max-width: 760px) {
  .shell {
    flex-direction: column;
    height: 100%;
    max-height: 100%;
    overflow: hidden;
  }

  .shell :deep(.teacher-sidebar) {
    position: relative;
    height: auto;
    max-height: none;
    flex-shrink: 0;
  }

  .toolbar-slot {
    padding-inline: 1rem;
  }
}
</style>
