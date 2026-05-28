import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type TeacherNotificationKind = 'assignment_published' | 'admin_announcement'

export interface TeacherNotification {
  id: string
  kind: TeacherNotificationKind
  title: string
  body: string
  createdAt: string
  read: boolean
}

function stateKey(userId: number | string) {
  return `plex-teacher-notif:${userId}`
}

function seenAnnouncementsKey(userId: number | string) {
  return `plex-teacher-announcement-seen:${userId}`
}

function readState(userId: number | string): TeacherNotification[] {
  try {
    const raw = localStorage.getItem(stateKey(userId))
    if (!raw) return []
    const parsed = JSON.parse(raw) as { items: TeacherNotification[] }
    return parsed?.items ?? []
  } catch {
    return []
  }
}

function writeState(userId: number | string, items: TeacherNotification[]) {
  localStorage.setItem(stateKey(userId), JSON.stringify({ items }))
}

function readSeenAnnouncementIds(userId: number | string): number[] {
  try {
    const raw = localStorage.getItem(seenAnnouncementsKey(userId))
    if (!raw) return []
    const parsed = JSON.parse(raw) as number[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeSeenAnnouncementIds(userId: number | string, ids: number[]) {
  localStorage.setItem(seenAnnouncementsKey(userId), JSON.stringify(ids))
}

export const useTeacherNotificationStore = defineStore('teacherNotifications', () => {
  const items = ref<TeacherNotification[]>([])

  const unreadCount = computed(() => items.value.filter((n) => !n.read).length)

  function hydrate(userId: number | string) {
    items.value = readState(userId)
  }

  function persist(userId: number | string) {
    writeState(userId, items.value)
  }

  function push(
    userId: number | string,
    kind: TeacherNotificationKind,
    payload: { title: string; body: string },
  ) {
    const notification: TeacherNotification = {
      id: `${kind}-${Date.now()}`,
      kind,
      title: payload.title,
      body: payload.body,
      createdAt: new Date().toISOString(),
      read: false,
    }
    items.value = [notification, ...items.value].slice(0, 50)
    persist(userId)
    return notification
  }

  function notifyAssignmentPublished(userId: number | string, title: string, studentCount: number) {
    return push(userId, 'assignment_published', {
      title: '作业发布成功',
      body:
        studentCount > 0
          ? `「${title}」已发布，已通知 ${studentCount} 名学生。`
          : `「${title}」已发布。`,
    })
  }

  function syncAdminAnnouncements(
    userId: number | string,
    announcements: Array<{ id: number; title: string; body: string }>,
  ) {
    const seen = new Set(readSeenAnnouncementIds(userId))
    let added = false
    for (const ann of announcements) {
      if (seen.has(ann.id)) continue
      push(userId, 'admin_announcement', {
        title: `管理员公告：${ann.title}`,
        body: ann.body,
      })
      seen.add(ann.id)
      added = true
    }
    if (added) {
      writeSeenAnnouncementIds(userId, [...seen])
    }
  }

  function markRead(userId: number | string, id: string) {
    items.value = items.value.map((n) => (n.id === id ? { ...n, read: true } : n))
    persist(userId)
  }

  function markAllRead(userId: number | string) {
    items.value = items.value.map((n) => ({ ...n, read: true }))
    persist(userId)
  }

  function clearForLogout() {
    items.value = []
  }

  return {
    items,
    unreadCount,
    hydrate,
    push,
    notifyAssignmentPublished,
    syncAdminAnnouncements,
    markRead,
    markAllRead,
    clearForLogout,
  }
})
