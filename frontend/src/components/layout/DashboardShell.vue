<script setup lang="ts">
import { inject, onBeforeUnmount, provide, ref, watchEffect } from 'vue'
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

watchEffect(() => {
  if (contentOnly) {
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
      <PlexTopbar
        v-model:search="searchText"
        :title="pageTitle"
        :subtitle="pageSubtitle"
        :placeholder="searchPlaceholder"
        :hide-search="hideSearch"
        @search-submit="(q) => $emit('searchSubmit', q)"
      />

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

  <!-- 子页面：只输出内容，工具条传送到宿主 -->
  <template v-else>
    <Teleport defer :to="`#${TOOLBAR_TARGET_ID}`">
      <slot name="toolbar" />
    </Teleport>
    <slot />
  </template>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100%;
  background: var(--plex-bg, #050a0e);
  color: var(--plex-text, #e2e8f0);
  font-family:
    'Outfit',
    'Noto Sans SC',
    system-ui,
    sans-serif;
}

.shell--collapsed :deep(.sidebar) {
  width: 72px;
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.toolbar-slot {
  width: 100%;
  min-height: 0;
}

.main-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.topbar-actions {
  padding: 0 1.25rem;
}

.view-switch {
  display: inline-flex !important;
  align-items: center;
  gap: 0.4rem;
}
</style>
