<script setup lang="ts">
import { inject, onActivated, onBeforeUnmount, onDeactivated, provide, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NButton } from 'naive-ui'
import { MapOutline } from '@vicons/ionicons5'
import PlexSidebar from './PlexSidebar.vue'
import type { StudentNavKey } from './PlexSidebar.vue'
import PlexTopbar from './PlexTopbar.vue'
import PlexGuideTour from '../common/PlexGuideTour.vue'
import { applyStudentShellChrome } from '../../composables/useStudentShellChrome'

const STUDENT_SHELL_NESTED = 'plex-student-shell-nested'
const TOOLBAR_TARGET_ID = 'plex-student-shell-toolbar'

const props = withDefaults(
  defineProps<{
    activeNav: StudentNavKey
    pageTitle: string
    pageSubtitle?: string
    searchPlaceholder: string
    showViewSwitcher?: boolean
    hideSearch?: boolean
    /** 由 StudentShellLayout 使用：真正渲染侧栏/顶栏 */
    layoutHost?: boolean
  }>(),
  {
    pageSubtitle: '每一步探索，都是成长的轨迹',
    showViewSwitcher: false,
    hideSearch: false,
    layoutHost: false,
  },
)

defineEmits<{
  viewSwitch: [key: string]
  searchSubmit: [query: string]
}>()

const router = useRouter()
const nested = inject(STUDENT_SHELL_NESTED, false)
const isHost = props.layoutHost || !nested
const contentOnly = !isHost

if (isHost) {
  provide(STUDENT_SHELL_NESTED, true)
}

const sidebarCollapsed = ref(false)
const searchText = ref('')
/** KeepAlive 停用时关闭 Teleport，避免多页工具条叠在同一宿主节点 */
const shellActive = ref(true)

onActivated(() => {
  shellActive.value = true
})

onDeactivated(() => {
  shellActive.value = false
})

watchEffect(() => {
  if (contentOnly && shellActive.value) {
    applyStudentShellChrome({
      activeNav: props.activeNav,
      pageTitle: props.pageTitle,
      pageSubtitle: props.pageSubtitle || '每一步探索，都是成长的轨迹',
      searchPlaceholder: props.searchPlaceholder,
      hideSearch: props.hideSearch,
      showViewSwitcher: props.showViewSwitcher,
    })
  }
})

onBeforeUnmount(() => {
  // 离开内容页时不重置 chrome，避免闪回默认标题
})

function goStarMap() {
  void router.push('/student/star-path')
}
</script>

<template>
  <!-- 布局宿主：侧栏/顶栏常驻 -->
  <div v-if="isHost" class="shell" :class="{ 'shell--collapsed': sidebarCollapsed }">
    <PlexSidebar v-model:collapsed="sidebarCollapsed" :active-key="activeNav" />

    <div class="main">
      <div class="topbar-slot">
        <PlexTopbar
          v-model:search="searchText"
          :title="pageTitle"
          :subtitle="pageSubtitle"
          :placeholder="searchPlaceholder"
          :hide-search="hideSearch"
          @search-submit="(q) => $emit('searchSubmit', q)"
        />
      </div>

      <div v-if="showViewSwitcher" class="topbar-actions">
        <n-button secondary round size="small" class="view-switch" @click="goStarMap">
          <n-icon :component="MapOutline" :size="18" />
          <span class="view-switch__text">查看星图</span>
        </n-button>
      </div>

      <div :id="TOOLBAR_TARGET_ID" class="toolbar-slot">
        <slot name="toolbar" />
      </div>

      <div class="main-body">
        <slot />
      </div>
    </div>
    <PlexGuideTour v-if="activeNav" role="student" />
  </div>

  <!-- 子页面：只输出内容；工具条仅在激活时传送，防止 KeepAlive 叠层 -->
  <template v-else>
    <Teleport v-if="shellActive" defer :to="`#${TOOLBAR_TARGET_ID}`">
      <slot name="toolbar" />
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
  background: var(--plex-bg, #050a0e);
  color: var(--plex-text, #e2e8f0);
  font-family:
    'Outfit',
    'Noto Sans SC',
    system-ui,
    sans-serif;
}

.shell :deep(.plex-sidebar) {
  position: sticky;
  top: 0;
  align-self: stretch;
  height: 100%;
  max-height: 100%;
  flex-shrink: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

.shell--collapsed :deep(.sidebar),
.shell--collapsed :deep(.plex-sidebar) {
  width: 72px;
}

.main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.topbar-slot {
  position: relative;
  z-index: 7;
  flex-shrink: 0;
}

.toolbar-slot {
  position: relative;
  z-index: 6;
  flex-shrink: 0;
  width: 100%;
  min-height: 0;
  background: rgba(2, 12, 21, 0.96);
  border-bottom: 1px solid rgba(37, 245, 238, 0.08);
}

.main-body {
  position: relative;
  z-index: 1;
  flex: 1;
  min-width: 0;
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
  z-index: 5;
  flex-shrink: 0;
  padding: 0 1.25rem;
}

.view-switch {
  display: inline-flex !important;
  align-items: center;
  gap: 0.4rem;
}
</style>
