<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  ArchiveOutline,
  BarbellOutline,
  CompassOutline,
  PlanetOutline,
  SettingsOutline,
} from '@vicons/ionicons5'
import { useAuthStore } from '../../stores/auth'

export type TeacherNavKey = 'navigator' | 'starfield' | 'trial' | 'explorers' | 'admin'

const props = withDefaults(
  defineProps<{
    activeKey: TeacherNavKey
    collapsed?: boolean
  }>(),
  {
    collapsed: false,
  },
)

const emit = defineEmits<{
  'update:collapsed': [value: boolean]
}>()

const auth = useAuthStore()

const allNavItems = [
  { key: 'navigator' as const, label: '领航总览', sub: 'NAVIGATOR HUB', icon: CompassOutline, to: '/teacher' },
  { key: 'starfield' as const, label: '星域观测', sub: 'STARFIELD ANALYTICS', icon: PlanetOutline, to: '/teacher/starfield' },
  { key: 'trial' as const, label: '试炼中枢', sub: 'TRIAL COMMAND', icon: BarbellOutline, to: '/teacher/trials' },
  { key: 'explorers' as const, label: 'Explorer 档案', sub: 'EXPLORER ARCHIVES', icon: ArchiveOutline, to: '/teacher/explorers' },
  { key: 'admin' as const, label: '控制中枢', sub: 'CONTROL CENTER', icon: SettingsOutline, to: '/admin' },
]

const navItems = computed(() =>
  auth.profile?.role === 'admin' ? allNavItems : allNavItems.filter((item) => item.key !== 'admin'),
)

function toggleCollapsed() {
  emit('update:collapsed', !props.collapsed)
}
</script>

<template>
  <aside
    class="teacher-sidebar"
    :class="{ 'teacher-sidebar--collapsed': collapsed }"
    aria-label="教师端主导航"
  >
    <div class="teacher-sidebar__brand">
      <svg class="teacher-brand-mark" viewBox="0 0 48 48" width="32" height="32" aria-hidden="true">
        <path fill="currentColor" d="M24 3l5.1 15.9L45 24l-15.9 5.1L24 45l-5.1-15.9L3 24l15.9-5.1L24 3z" />
        <path fill="#1a0f05" d="M24 13l2.2 8.8L35 24l-8.8 2.2L24 35l-2.2-8.8L13 24l8.8-2.2L24 13z" />
      </svg>
      <span v-if="!collapsed" class="teacher-sidebar__name">PLEX</span>
    </div>

    <nav class="teacher-sidebar__nav" aria-label="教师端页面导航">
      <RouterLink
        v-for="item in navItems"
        :key="item.key"
        :to="item.to"
        class="teacher-nav"
        :class="{ 'teacher-nav--active': item.key === activeKey }"
      >
        <span class="teacher-nav__bar" aria-hidden="true" />
        <n-icon :component="item.icon" class="teacher-nav__icon" />
        <span v-if="!collapsed" class="teacher-nav__copy">
          <span class="teacher-nav__label">{{ item.label }}</span>
          <span class="teacher-nav__sub">{{ item.sub }}</span>
        </span>
      </RouterLink>
    </nav>

    <div class="teacher-sidebar__dock">
      <div v-if="!collapsed" class="teacher-sidebar__footer">
        <span class="teacher-sidebar__keeper-avatar" aria-hidden="true"><span /></span>
        <div class="teacher-sidebar__keeper-copy">
          <strong>Waystation Keeper</strong>
          <small>AI Observation · 在线</small>
        </div>
      </div>

      <button type="button" class="teacher-sidebar__collapse" aria-label="收起侧栏" @click="toggleCollapsed">
        <span aria-hidden="true">«</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.teacher-sidebar {
  position: relative;
  z-index: 4;
  width: 230px;
  height: 100%;
  min-height: 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 2.25rem 0 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 22% 8%, rgba(251, 146, 60, 0.1), transparent 26%),
    linear-gradient(180deg, rgba(12, 8, 4, 0.98), rgba(5, 8, 14, 0.99));
  border-right: 1px solid rgba(251, 146, 60, 0.14);
  transition: width 0.2s ease;
}

.teacher-sidebar--collapsed {
  width: 84px;
}

.teacher-sidebar__brand {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 2.55rem 1.75rem;
  color: #fb923c;
}

.teacher-brand-mark {
  flex: 0 0 auto;
  filter: drop-shadow(0 0 12px rgba(251, 146, 60, 0.65));
}

.teacher-sidebar__name {
  color: #ffffff;
  font-size: 1.75rem;
  font-weight: 760;
  letter-spacing: 0.08em;
}

.teacher-sidebar__nav {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.55rem;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: rgba(251, 146, 60, 0.35) transparent;
}

.teacher-nav {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 76px;
  gap: 0.95rem;
  padding: 0.7rem 1.35rem 0.7rem 2.55rem;
  color: rgba(255, 237, 213, 0.72);
  text-decoration: none;
  transition: background 0.18s ease, color 0.18s ease;
}

.teacher-sidebar--collapsed .teacher-nav {
  justify-content: center;
  padding: 0.7rem 0;
}

.teacher-nav:hover {
  color: #fff7ed;
  background: rgba(251, 146, 60, 0.05);
}

.teacher-nav--active {
  color: #fff7ed;
  background:
    linear-gradient(90deg, rgba(251, 146, 60, 0.28), rgba(251, 146, 60, 0.08) 72%, transparent),
    rgba(251, 146, 60, 0.04);
}

.teacher-nav__bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  opacity: 0;
  background: linear-gradient(180deg, #fbbf24, #fb923c);
  box-shadow: 0 0 18px rgba(251, 146, 60, 0.76);
}

.teacher-nav--active .teacher-nav__bar {
  opacity: 1;
}

.teacher-nav__icon {
  flex: 0 0 auto;
  font-size: 1.95rem;
}

.teacher-nav__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
  line-height: 1.1;
}

.teacher-nav__label {
  font-size: 1rem;
  font-weight: 670;
  white-space: nowrap;
}

.teacher-nav__sub {
  color: rgba(255, 237, 213, 0.5);
  font-size: 0.68rem;
  font-weight: 680;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.teacher-nav--active .teacher-nav__label,
.teacher-nav--active .teacher-nav__sub {
  color: #fdba74;
  text-shadow: 0 0 14px rgba(251, 146, 60, 0.45);
}

.teacher-sidebar__dock {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.65rem;
  margin-top: auto;
  padding: 0.75rem 1.35rem 1.25rem;
  border-top: 1px solid rgba(251, 146, 60, 0.08);
  background: linear-gradient(180deg, transparent, rgba(5, 8, 14, 0.92) 28%);
}

.teacher-sidebar__footer {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.7rem 0.85rem;
  border: 1px solid rgba(251, 146, 60, 0.12);
  border-radius: 14px;
  background: rgba(8, 14, 22, 0.72);
}

.teacher-sidebar__keeper-copy {
  min-width: 0;
}

.teacher-sidebar__keeper-avatar {
  display: grid;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: #061827;
}

.teacher-sidebar__keeper-avatar span {
  width: 24px;
  height: 18px;
  border-radius: 8px;
  background: #e9f3fb;
  box-shadow: inset 0 -6px #111926;
}

.teacher-sidebar__keeper-copy strong {
  display: block;
  overflow: hidden;
  color: rgba(255, 247, 237, 0.9);
  font-size: 0.8rem;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.teacher-sidebar__keeper-copy small {
  display: block;
  overflow: hidden;
  color: rgba(221, 230, 239, 0.55);
  font-size: 0.68rem;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.teacher-sidebar__collapse {
  width: 48px;
  height: 48px;
  align-self: center;
  flex-shrink: 0;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 50%;
  background: rgba(20, 14, 8, 0.68);
  color: #fed7aa;
  cursor: pointer;
  font-size: 1.35rem;
}

.teacher-sidebar--collapsed .teacher-sidebar__dock {
  padding-inline: 0.5rem;
}

@media (max-width: 760px) {
  .teacher-sidebar,
  .teacher-sidebar--collapsed {
    width: 100%;
    min-height: auto;
    padding: 1rem 1rem 0.75rem;
    border-right: 0;
    border-bottom: 1px solid rgba(251, 146, 60, 0.12);
  }

  .teacher-sidebar__brand {
    justify-content: center;
    padding: 0 0 0.9rem;
  }

  .teacher-sidebar__nav {
    flex: 0 0 auto;
    flex-direction: row;
    gap: 0.35rem;
    overflow-x: auto;
    padding-bottom: 0.35rem;
  }

  .teacher-nav,
  .teacher-sidebar--collapsed .teacher-nav {
    min-width: 120px;
    min-height: 54px;
    justify-content: center;
    padding: 0.55rem 0.75rem;
  }

  .teacher-nav__copy,
  .teacher-sidebar__footer {
    display: none;
  }

  .teacher-sidebar__dock {
    display: none;
  }
}
</style>
