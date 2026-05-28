<script setup lang="ts">
import { computed, h, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NAvatar,
  NBadge,
  NButton,
  NDropdown,
  NEmpty,
  NIcon,
  NInput,
  NPopover,
  type DropdownOption,
} from 'naive-ui'
import { ChevronDownOutline, ExitOutline, NotificationsOutline, SearchOutline } from '@vicons/ionicons5'
import { useAuthStore } from '../../stores/auth'
import { useNotificationStore } from '../../stores/notifications'
import { useTeacherNotificationStore } from '../../stores/teacherNotifications'
import { useStudentNotificationSync } from '../../composables/useStudentNotificationSync'
import { useTeacherNotificationSync } from '../../composables/useTeacherNotificationSync'

withDefaults(
  defineProps<{
    title: string
    subtitle: string
    placeholder?: string
    keyboardHint?: string
    hideSearch?: boolean
  }>(),
  {
    placeholder: '搜索知识点、试炼或星域',
    keyboardHint: '',
    hideSearch: false,
  },
)

const search = defineModel<string>('search', { default: '' })

const auth = useAuthStore()
const studentNotifications = useNotificationStore()
const teacherNotifications = useTeacherNotificationStore()
const router = useRouter()
const showNotifications = ref(false)

const isStudent = computed(() => auth.profile?.role === 'student')
const isTeacher = computed(() => {
  const role = auth.profile?.role
  return role === 'teacher' || role === 'admin'
})

useStudentNotificationSync()
useTeacherNotificationSync()

const displayName = computed(() => auth.profile?.real_name || auth.profile?.username || '张子轩')
const userLevel = computed(() => auth.profile?.level ?? 18)
const userOptions: DropdownOption[] = [
  {
    label: '退出登录',
    key: 'logout',
    icon: () => h(ExitOutline),
  },
]

const notificationItems = computed(() => {
  if (isStudent.value) return studentNotifications.items
  if (isTeacher.value) return teacherNotifications.items
  return []
})

const unreadCount = computed(() => {
  if (isStudent.value) return studentNotifications.unreadCount
  if (isTeacher.value) return teacherNotifications.unreadCount
  return 0
})

const showNotificationPanel = computed(() => isStudent.value || isTeacher.value)

function formatTime(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function onNotificationOpen(show: boolean) {
  showNotifications.value = show
}

function markAllRead() {
  const id = auth.profile?.id
  if (!id) return
  if (isStudent.value) studentNotifications.markAllRead(id)
  else if (isTeacher.value) teacherNotifications.markAllRead(id)
}

function onNotificationClick(id: string) {
  const uid = auth.profile?.id
  if (!uid) return
  if (isStudent.value) studentNotifications.markRead(uid, id)
  else if (isTeacher.value) teacherNotifications.markRead(uid, id)
}

async function handleUserSelect(key: string) {
  if (key !== 'logout') return
  studentNotifications.clearForLogout()
  teacherNotifications.clearForLogout()
  await auth.logout()
  await router.replace({ name: 'login' })
}
</script>

<template>
  <header class="plex-topbar" :class="{ 'plex-topbar--compact': hideSearch }">
    <div class="plex-topbar__heading">
      <h1>{{ title }}<span aria-hidden="true" /></h1>
      <p>{{ subtitle }}</p>
    </div>

    <div v-if="!hideSearch" class="plex-topbar__search">
      <n-input v-model:value="search" round :placeholder="placeholder" clearable class="plex-topbar__input">
        <template #prefix>
          <n-icon :component="SearchOutline" class="plex-topbar__search-icon" />
        </template>
        <template v-if="keyboardHint" #suffix>
          <span class="plex-topbar__kbd">{{ keyboardHint }}</span>
        </template>
      </n-input>
    </div>

    <div class="plex-topbar__userbar">
      <n-popover
        v-if="showNotificationPanel"
        trigger="click"
        placement="bottom-end"
        :show="showNotifications"
        class="plex-notif-popover"
        @update:show="onNotificationOpen"
      >
        <template #trigger>
          <n-badge :value="unreadCount || undefined" :max="9" type="error" :offset="[-2, 4]">
            <button type="button" class="plex-topbar__icon-btn" aria-label="通知">
              <n-icon :component="NotificationsOutline" :size="25" />
            </button>
          </n-badge>
        </template>
        <div class="plex-notif-panel">
          <header class="plex-notif-panel__head">
            <strong>通知</strong>
            <n-button
              v-if="notificationItems.length"
              text
              size="tiny"
              type="primary"
              @click="markAllRead"
            >
              全部已读
            </n-button>
          </header>
          <ul v-if="notificationItems.length" class="plex-notif-panel__list">
            <li
              v-for="item in notificationItems"
              :key="item.id"
              class="plex-notif-item"
              :class="{ 'plex-notif-item--unread': !item.read }"
              @click="onNotificationClick(item.id)"
            >
              <div class="plex-notif-item__title">{{ item.title }}</div>
              <p class="plex-notif-item__body">{{ item.body }}</p>
              <time class="plex-notif-item__time">{{ formatTime(item.createdAt) }}</time>
            </li>
          </ul>
          <n-empty v-else size="small" description="暂无通知" class="plex-notif-panel__empty" />
        </div>
      </n-popover>
      <n-badge v-else dot type="success" :offset="[-1, 5]">
        <button type="button" class="plex-topbar__icon-btn" aria-label="通知">
          <n-icon :component="NotificationsOutline" :size="25" />
        </button>
      </n-badge>
      <span class="plex-topbar__divider" />
      <n-dropdown trigger="click" :options="userOptions" @select="handleUserSelect">
        <button type="button" class="plex-topbar__user" aria-label="打开用户菜单">
          <n-avatar round :size="52" class="plex-topbar__avatar">
            <span class="plex-avatar-bot" aria-hidden="true">
              <span class="plex-avatar-bot__head" />
            </span>
          </n-avatar>
          <span class="plex-topbar__copy">
            <strong>{{ displayName }}</strong>
            <em>Lv.{{ userLevel }}</em>
          </span>
          <n-icon :component="ChevronDownOutline" :size="20" />
        </button>
      </n-dropdown>
    </div>
  </header>
</template>

<style scoped>
.plex-topbar {
  position: relative;
  z-index: 3;
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(320px, 540px) minmax(260px, 1fr);
  align-items: start;
  gap: 1.5rem;
  padding: 1.35rem var(--plex-page-gutter-x) 0;
}

.plex-topbar--compact {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 1rem 1.5rem;
}

.plex-topbar--compact .plex-topbar__heading {
  grid-column: 1;
  grid-row: 1;
  min-width: 0;
}

.plex-topbar--compact .plex-topbar__userbar {
  grid-column: 2;
  grid-row: 1;
  flex-shrink: 0;
}

.plex-topbar__heading h1 {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin: 0;
  color: #ffffff;
  font-size: clamp(1.7rem, 2.2vw, 2.25rem);
  font-weight: 740;
  line-height: 1.1;
}

.plex-topbar__heading h1 span {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #2efff1;
  box-shadow: 0 0 12px rgba(46, 255, 241, 0.85);
}

.plex-topbar__heading p {
  margin: 0.7rem 0 0;
  color: rgba(221, 230, 239, 0.72);
  font-size: 0.98rem;
}

.plex-topbar__input :deep(.n-input) {
  font-size: 0.96rem;
  --n-height: 58px !important;
  --n-color: rgba(6, 18, 31, 0.66) !important;
  --n-color-focus: rgba(8, 24, 39, 0.86) !important;
  --n-border: 1px solid rgba(130, 212, 255, 0.12) !important;
  --n-border-hover: 1px solid rgba(37, 245, 238, 0.32) !important;
  --n-text-color: #edf7ff !important;
  --n-placeholder-color: rgba(210, 225, 238, 0.55) !important;
}

.plex-topbar__search-icon {
  color: #e8f9ff;
  font-size: 1.35rem;
}

.plex-topbar__kbd {
  color: rgba(221, 230, 239, 0.58);
  border: 1px solid rgba(221, 230, 239, 0.16);
  border-radius: 0.35rem;
  padding: 0.08rem 0.35rem;
  font-size: 0.75rem;
}

.plex-topbar__userbar {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 1.3rem;
}

.plex-topbar__divider {
  width: 1px;
  height: 40px;
  background: rgba(219, 235, 249, 0.1);
}

.plex-topbar__icon-btn {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #edf7ff;
  cursor: pointer;
}

.plex-topbar__user {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  border: 0;
  background: transparent;
  color: #ffffff;
  cursor: pointer;
}

.plex-topbar__avatar {
  border: 1px solid rgba(160, 211, 244, 0.26);
  background:
    radial-gradient(circle, rgba(82, 157, 255, 0.22), transparent 62%),
    #061827 !important;
  box-shadow:
    0 0 0 5px rgba(87, 139, 191, 0.1),
    0 0 18px rgba(37, 245, 238, 0.22);
}

.plex-avatar-bot {
  position: relative;
  display: grid;
  width: 31px;
  height: 24px;
  place-items: center;
}

.plex-avatar-bot__head {
  width: 28px;
  height: 20px;
  border-radius: 9px;
  background: #e9f3fb;
  box-shadow: inset 0 -8px #111926;
}

.plex-avatar-bot__head::before,
.plex-avatar-bot__head::after {
  position: absolute;
  top: 13px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #36fff1;
  box-shadow: 0 0 7px rgba(54, 255, 241, 0.9);
  content: '';
}

.plex-avatar-bot__head::before {
  left: 9px;
}

.plex-avatar-bot__head::after {
  right: 9px;
}

.plex-topbar__copy {
  display: grid;
  gap: 0.2rem;
  text-align: left;
}

.plex-topbar__copy strong {
  font-size: 0.96rem;
}

.plex-topbar__copy em {
  width: fit-content;
  padding: 0.04rem 0.34rem;
  border-radius: 0.35rem;
  background: rgba(37, 245, 238, 0.18);
  color: #57fff2;
  font-size: 0.76rem;
  font-style: normal;
}

.plex-notif-panel {
  width: min(360px, 92vw);
  max-height: 420px;
  display: flex;
  flex-direction: column;
}

.plex-notif-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.35rem 0.15rem 0.65rem;
  border-bottom: 1px solid rgba(130, 212, 255, 0.12);
  color: #edf7ff;
}

.plex-notif-panel__list {
  list-style: none;
  margin: 0;
  padding: 0.35rem 0 0;
  overflow-y: auto;
  max-height: 340px;
}

.plex-notif-item {
  padding: 0.65rem 0.5rem;
  border-radius: 0.45rem;
  cursor: pointer;
  transition: background 0.15s;
}

.plex-notif-item:hover {
  background: rgba(37, 245, 238, 0.06);
}

.plex-notif-item--unread {
  background: rgba(16, 240, 192, 0.08);
}

.plex-notif-item__title {
  color: #ffffff;
  font-size: 0.88rem;
  font-weight: 680;
}

.plex-notif-item__body {
  margin: 0.25rem 0 0;
  color: rgba(224, 237, 247, 0.78);
  font-size: 0.82rem;
  line-height: 1.5;
}

.plex-notif-item__time {
  display: block;
  margin-top: 0.35rem;
  color: rgba(142, 163, 184, 0.85);
  font-size: 0.72rem;
}

.plex-notif-panel__empty {
  padding: 1.5rem 0;
}

@media (max-width: 1280px) {
  .plex-topbar {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .plex-topbar__userbar {
    justify-self: start;
  }
}

@media (max-width: 900px) {
  .plex-topbar {
    padding-inline: 1rem;
  }
}
</style>
