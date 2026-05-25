<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  ArchiveOutline,
  BarbellOutline,
  CalendarOutline,
  GitNetworkOutline,
  MailOutline,
  RocketOutline,
} from '@vicons/ionicons5'

type NavKey = 'cabin' | 'track' | 'trial' | 'messenger' | 'daily' | 'archive' | 'admin'

const props = withDefaults(
  defineProps<{
    activeKey: NavKey
    collapsed?: boolean
  }>(),
  {
    collapsed: false,
  },
)

const emit = defineEmits<{
  'update:collapsed': [value: boolean]
}>()

const navItems = computed(() => [
  { key: 'cabin' as const, label: '探索舱', sub: 'EXPLORER', icon: RocketOutline, to: '/discovery' },
  { key: 'track' as const, label: '星轨路径', sub: 'STARPATH', icon: GitNetworkOutline, to: '/star-path' },
  { key: 'trial' as const, label: '试炼关卡', sub: 'TRIAL ARENA', icon: BarbellOutline, to: '/trial-arena' },
  { key: 'messenger' as const, label: '驿站使者', sub: 'MESSENGER', icon: MailOutline, to: '/messenger' },
  { key: 'daily' as const, label: '今日委托', sub: 'DAILY QUEST', icon: CalendarOutline, to: '/daily' },
  { key: 'archive' as const, label: '探索档案', sub: 'ARCHIVES', icon: ArchiveOutline, to: '/archives' },
])

function toggleCollapsed() {
  emit('update:collapsed', !props.collapsed)
}
</script>

<template>
  <aside class="plex-sidebar" :class="{ 'plex-sidebar--collapsed': collapsed }" aria-label="主导航">
    <div class="plex-sidebar__brand">
      <svg class="plex-brand-mark" viewBox="0 0 48 48" width="32" height="32" aria-hidden="true">
        <path fill="currentColor" d="M24 3l5.1 15.9L45 24l-15.9 5.1L24 45l-5.1-15.9L3 24l15.9-5.1L24 3z" />
        <path fill="#031019" d="M24 13l2.2 8.8L35 24l-8.8 2.2L24 35l-2.2-8.8L13 24l8.8-2.2L24 13z" />
      </svg>
      <span v-if="!collapsed" class="plex-sidebar__name">PLEX</span>
    </div>

    <nav class="plex-sidebar__nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.key"
        :to="item.to"
        class="plex-nav"
        :class="{ 'plex-nav--active': item.key === activeKey }"
      >
        <span class="plex-nav__bar" aria-hidden="true" />
        <n-icon :component="item.icon" class="plex-nav__icon" />
        <span v-if="!collapsed" class="plex-nav__copy">
          <span class="plex-nav__label">{{ item.label }}</span>
          <span class="plex-nav__sub">{{ item.sub }}</span>
        </span>
      </RouterLink>
    </nav>

    <button type="button" class="plex-sidebar__collapse" aria-label="收起侧栏" @click="toggleCollapsed">
      <span aria-hidden="true">«</span>
    </button>
  </aside>
</template>

<style scoped>
.plex-sidebar {
  position: relative;
  z-index: 4;
  width: 230px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 2.25rem 0 1.5rem;
  background:
    radial-gradient(circle at 22% 8%, rgba(20, 241, 226, 0.08), transparent 26%),
    linear-gradient(180deg, rgba(3, 15, 25, 0.98), rgba(1, 8, 15, 0.99));
  border-right: 1px solid rgba(110, 228, 255, 0.11);
  transition: width 0.2s ease;
}

.plex-sidebar--collapsed {
  width: 84px;
}

.plex-sidebar__brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 2.55rem 2.85rem;
  color: #25f5ee;
}

.plex-brand-mark {
  flex: 0 0 auto;
  filter: drop-shadow(0 0 12px rgba(37, 245, 238, 0.65));
}

.plex-sidebar__name {
  color: #ffffff;
  font-size: 1.75rem;
  font-weight: 760;
  letter-spacing: 0.08em;
}

.plex-sidebar__nav {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.55rem;
}

.plex-nav {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 76px;
  gap: 0.95rem;
  padding: 0.7rem 1.35rem 0.7rem 2.55rem;
  color: rgba(220, 230, 241, 0.74);
  text-decoration: none;
  transition:
    background 0.18s ease,
    color 0.18s ease;
}

.plex-sidebar--collapsed .plex-nav {
  justify-content: center;
  padding: 0.7rem 0;
}

.plex-nav:hover {
  color: #ffffff;
  background: rgba(37, 245, 238, 0.045);
}

.plex-nav--active {
  color: #ffffff;
  background:
    linear-gradient(90deg, rgba(16, 240, 192, 0.25), rgba(16, 240, 192, 0.07) 72%, transparent),
    rgba(6, 182, 212, 0.04);
}

.plex-nav__bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  opacity: 0;
  background: linear-gradient(180deg, #5ffff3, #12d8c8);
  box-shadow: 0 0 18px rgba(37, 245, 238, 0.76);
}

.plex-nav--active .plex-nav__bar {
  opacity: 1;
}

.plex-nav__icon {
  flex: 0 0 auto;
  font-size: 1.95rem;
}

.plex-nav__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
  line-height: 1.1;
}

.plex-nav__label {
  font-size: 1rem;
  font-weight: 670;
  white-space: nowrap;
}

.plex-nav__sub {
  color: rgba(221, 230, 239, 0.55);
  font-size: 0.72rem;
  font-weight: 680;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.plex-nav--active .plex-nav__label,
.plex-nav--active .plex-nav__sub {
  color: #52fff1;
  text-shadow: 0 0 14px rgba(37, 245, 238, 0.5);
}

.plex-sidebar__collapse {
  width: 56px;
  height: 56px;
  align-self: center;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 50%;
  background: rgba(12, 27, 40, 0.68);
  color: #d9f4ff;
  cursor: pointer;
  font-size: 1.5rem;
}

@media (max-width: 760px) {
  .plex-sidebar,
  .plex-sidebar--collapsed {
    width: 100%;
    min-height: auto;
    padding: 1rem 1rem 0.75rem;
    border-right: 0;
    border-bottom: 1px solid rgba(110, 228, 255, 0.12);
  }

  .plex-sidebar__brand {
    justify-content: center;
    padding: 0 0 0.9rem;
  }

  .plex-sidebar__nav {
    flex: 0 0 auto;
    flex-direction: row;
    gap: 0.35rem;
    overflow-x: auto;
    padding-bottom: 0.35rem;
  }

  .plex-nav,
  .plex-sidebar--collapsed .plex-nav {
    min-width: 120px;
    min-height: 54px;
    justify-content: center;
    padding: 0.55rem 0.75rem;
  }

  .plex-nav__copy {
    display: none;
  }

  .plex-sidebar__collapse {
    display: none;
  }
}
</style>
