<script setup lang="ts">
import { ref } from 'vue'
import {
  NIcon,
  NButton,
  NDropdown,
  type DropdownOption,
} from 'naive-ui'
import {
  ChevronDownOutline,
  MapOutline,
} from '@vicons/ionicons5'
import PlexSidebar from './PlexSidebar.vue'
import PlexTopbar from './PlexTopbar.vue'

const props = withDefaults(
  defineProps<{
    activeNav: 'cabin' | 'track' | 'trial' | 'messenger' | 'daily' | 'archive' | 'control'
    pageTitle: string
    pageSubtitle?: string
    searchPlaceholder: string
    showViewSwitcher?: boolean
    hideSearch?: boolean
  }>(),
  { pageSubtitle: '每一步探索，都是成长的轨迹', showViewSwitcher: false, hideSearch: false },
)

const emit = defineEmits<{
  viewSwitch: [key: string]
}>()

const sidebarCollapsed = ref(false)
const searchText = ref('')

const viewOptions: DropdownOption[] = [
  { label: '路线图', key: 'roadmap' },
  { label: '列表视图', key: 'list' },
]


function onViewSelect(key: string) {
  emit('viewSwitch', key)
}
</script>

<template>
  <div class="shell" :class="{ 'shell--collapsed': sidebarCollapsed }">
    <PlexSidebar v-model:collapsed="sidebarCollapsed" :active-key="activeNav" />

    <div class="main">
      <PlexTopbar
        v-model:search="searchText"
        :title="pageTitle"
        :subtitle="pageSubtitle"
        :placeholder="searchPlaceholder"
        :hide-search="hideSearch"
      />

      <div v-if="showViewSwitcher" class="topbar-actions">
        <n-dropdown trigger="click" :options="viewOptions" @select="onViewSelect">
          <n-button secondary round size="small" class="view-switch">
            <n-icon :component="MapOutline" :size="18" />
            <span class="view-switch__text">切换视图</span>
            <n-icon :component="ChevronDownOutline" :size="16" />
          </n-button>
        </n-dropdown>
      </div>

      <div v-if="$slots.toolbar" class="toolbar-slot">
        <slot name="toolbar" />
      </div>

      <div class="main-body">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100%;
  background: #050a0e;
  color: #e2e8f0;
  font-family:
    'Outfit',
    'Noto Sans SC',
    system-ui,
    sans-serif;
}

.shell--collapsed .sidebar {
  width: 72px;
}

.sidebar {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 1.25rem 0.75rem;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(5, 10, 14, 0.98) 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  transition: width 0.2s ease;
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0 0.65rem 1.25rem;
  color: #00f2ff;
}

.sidebar__name {
  font-weight: 700;
  letter-spacing: 0.18em;
  font-size: 0.95rem;
  color: #f8fafc;
}

.sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.7rem 0.85rem;
  border-radius: 0.65rem;
  color: rgba(226, 232, 240, 0.72);
  text-decoration: none;
  font-size: 0.9rem;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #f1f5f9;
}

.nav-item--active {
  color: #00f2ff;
  background: rgba(0, 242, 255, 0.08);
  box-shadow: inset 0 0 24px rgba(0, 242, 255, 0.06);
}

.nav-item__accent {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  border-radius: 0 2px 2px 0;
  background: transparent;
}

.nav-item--active .nav-item__accent {
  height: 60%;
  background: linear-gradient(180deg, #00f2ff, #0891b2);
  box-shadow: 0 0 12px rgba(0, 242, 255, 0.55);
}

.nav-item__icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.nav-item__label {
  white-space: nowrap;
  overflow: hidden;
}

.sidebar__collapse {
  align-self: center;
  margin-top: 0.5rem;
  color: rgba(148, 163, 184, 0.8) !important;
}

.sidebar__chev {
  font-size: 1rem;
  letter-spacing: -0.1em;
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  position: relative;
  background:
    radial-gradient(ellipse 80% 50% at 50% -10%, rgba(0, 242, 255, 0.06), transparent),
    radial-gradient(ellipse 60% 40% at 90% 60%, rgba(59, 130, 246, 0.06), transparent),
    linear-gradient(180deg, #050a0e 0%, #030712 55%, #020617 100%);
}

.main::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.32;
  background-image: radial-gradient(1px 1px at 10% 20%, rgba(255, 255, 255, 0.2), transparent),
    radial-gradient(1px 1px at 80% 40%, rgba(255, 255, 255, 0.14), transparent);
  background-size: 320px 320px;
}

.topbar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-wrap: wrap;
}

.toolbar-slot {
  position: relative;
  z-index: 2;
  flex-shrink: 0;
}

.main-body {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.topbar__left {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.topbar__title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
}

.topbar__search {
  flex: 1;
  min-width: 200px;
  max-width: 480px;
  margin: 0 auto;
}

.topbar__input :deep(.n-input) {
  --n-color: rgba(15, 23, 42, 0.55) !important;
  --n-border: 1px solid rgba(255, 255, 255, 0.08) !important;
  --n-border-hover: 1px solid rgba(0, 242, 255, 0.28) !important;
  --n-text-color: #e2e8f0 !important;
  --n-placeholder-color: rgba(148, 163, 184, 0.65) !important;
}

.topbar__search-icon {
  color: rgba(148, 163, 184, 0.85);
}

.topbar__right {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-left: auto;
  flex-wrap: wrap;
}

.view-switch {
  display: inline-flex !important;
  align-items: center;
  gap: 0.4rem;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  background: rgba(15, 23, 42, 0.55) !important;
  color: #e2e8f0 !important;
}

.view-switch:hover {
  border-color: rgba(0, 242, 255, 0.35) !important;
}

.view-switch__text {
  font-size: 0.82rem;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 0.65rem;
  background: rgba(255, 255, 255, 0.04);
  color: #cbd5e1;
  cursor: pointer;
}

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #f1f5f9;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.5rem 0.25rem 0.35rem;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  color: inherit;
}

.user-chip:hover {
  border-color: rgba(0, 242, 255, 0.25);
}

.user-chip__avatar {
  background: linear-gradient(135deg, #0f172a, #1e293b) !important;
  color: #00f2ff !important;
  font-size: 0.85rem;
}

.user-chip__text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.15;
}

.user-chip__name {
  font-size: 0.85rem;
  font-weight: 500;
}

.user-chip__lv {
  font-size: 0.7rem;
  color: #00f2ff;
  font-weight: 600;
}

.user-chip__arrow {
  color: rgba(148, 163, 184, 0.8);
  margin-left: 0.15rem;
}

@media (max-width: 768px) {
  .shell {
    flex-direction: column;
  }

  .sidebar {
    width: 100% !important;
    flex-direction: row;
    flex-wrap: wrap;
    padding: 0.75rem;
  }

  .shell--collapsed .sidebar {
    width: 100% !important;
  }

  .sidebar__nav {
    flex-direction: row;
    flex-wrap: wrap;
    flex: 1;
  }

  .sidebar__collapse {
    display: none;
  }

  .topbar__search {
    order: 3;
    flex: 1 1 100%;
    max-width: none;
  }
}
</style>
