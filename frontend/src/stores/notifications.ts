import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type PlexNotificationKind =
  | 'welcome'
  | 'first_coding_solved'
  | 'teacher_task_published'
  | 'daily_quest_all_done'
  | 'system_announcement'

export interface PlexNotification {
  id: string
  kind: PlexNotificationKind
  title: string
  body: string
  createdAt: string
  read: boolean
}

const COPY: Record<
  PlexNotificationKind,
  { title: string; body: string }
> = {
  welcome: {
    title: '欢迎加入',
    body: '感谢加入 PLEX 宇宙，开启你的探索之旅吧。',
  },
  first_coding_solved: {
    title: '编程试炼',
    body: '你完成了第一道编程题，星轨又亮起了一盏灯。',
  },
  teacher_task_published: {
    title: '教师任务',
    body: '老师发布了新的任务，快去今日委托或探索舱查看。',
  },
  daily_quest_all_done: {
    title: '今日委托',
    body: '今日委托已全部完成，奖励反馈已解锁。',
  },
  system_announcement: {
    title: '系统公告',
    body: '管理员发布了新公告，请查阅。',
  },
}

function stateKey(userId: number | string) {
  return `plex-notif:${userId}`
}

function firedKey(userId: number | string) {
  return `plex-notif-fired:${userId}`
}

function assignmentsKey(userId: number | string) {
  return `plex-notif-assignments:${userId}`
}

interface PersistedState {
  items: PlexNotification[]
}

interface FiredState {
  welcome?: boolean
  first_coding_solved?: boolean
  /** YYYY-MM-DD，当日委托完成通知仅一次 */
  daily_quest_all_done_date?: string
}

function readState(userId: number | string): PersistedState {
  try {
    const raw = localStorage.getItem(stateKey(userId))
    if (!raw) return { items: [] }
    const parsed = JSON.parse(raw) as PersistedState
    return parsed?.items ? parsed : { items: [] }
  } catch {
    return { items: [] }
  }
}

function writeState(userId: number | string, items: PlexNotification[]) {
  localStorage.setItem(stateKey(userId), JSON.stringify({ items }))
}

function readFired(userId: number | string): FiredState {
  try {
    const raw = localStorage.getItem(firedKey(userId))
    if (!raw) return {}
    return JSON.parse(raw) as FiredState
  } catch {
    return {}
  }
}

function writeFired(userId: number | string, fired: FiredState) {
  localStorage.setItem(firedKey(userId), JSON.stringify(fired))
}

export function readKnownAssignmentIds(userId: number | string): number[] | null {
  try {
    const raw = localStorage.getItem(assignmentsKey(userId))
    if (raw === null) return null
    const parsed = JSON.parse(raw) as number[]
    return Array.isArray(parsed) ? parsed : null
  } catch {
    return null
  }
}

export function writeKnownAssignmentIds(userId: number | string, ids: number[]) {
  localStorage.setItem(assignmentsKey(userId), JSON.stringify(ids))
}

function todayKey() {
  return new Date().toISOString().slice(0, 10)
}

export const useNotificationStore = defineStore('notifications', () => {
  const items = ref<PlexNotification[]>([])

  const unreadCount = computed(() => items.value.filter((n) => !n.read).length)

  function hydrate(userId: number | string) {
    items.value = readState(userId).items
  }

  function persist(userId: number | string) {
    writeState(userId, items.value)
  }

  function push(
    userId: number | string,
    kind: PlexNotificationKind,
    extra?: { body?: string },
  ): PlexNotification | null {
    const fired = readFired(userId)
    if (kind === 'welcome' && fired.welcome) return null
    if (kind === 'first_coding_solved' && fired.first_coding_solved) return null
    if (kind === 'daily_quest_all_done') {
      if (fired.daily_quest_all_done_date === todayKey()) return null
    }
    // teacher_task_published 可多次（不同批次）

    const copy = COPY[kind]
    const notification: PlexNotification = {
      id: `${kind}-${Date.now()}`,
      kind,
      title: copy.title,
      body: extra?.body ?? copy.body,
      createdAt: new Date().toISOString(),
      read: false,
    }

    items.value = [notification, ...items.value].slice(0, 50)
    persist(userId)

    const nextFired: FiredState = { ...fired }
    if (kind === 'welcome') nextFired.welcome = true
    if (kind === 'first_coding_solved') nextFired.first_coding_solved = true
    if (kind === 'daily_quest_all_done') nextFired.daily_quest_all_done_date = todayKey()
    writeFired(userId, nextFired)

    return notification
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

  /** 合并服务端推送（教师发布作业等），按 server id 去重 */
  function ingestServer(
    userId: number | string,
    serverItems: Array<{ id: number; kind: string; title: string; body: string; created_at: string | null }>,
  ) {
    const seenKey = `plex-notif-server-seen:${userId}`
    let seen: number[] = []
    try {
      const raw = localStorage.getItem(seenKey)
      if (raw) seen = JSON.parse(raw) as number[]
    } catch {
      seen = []
    }
    const seenSet = new Set(seen)
    let added = false
    for (const row of serverItems) {
      if (seenSet.has(row.id)) continue
      const kind =
        row.kind === 'teacher_task_published' ? 'teacher_task_published' : 'teacher_task_published'
      if (kind !== 'teacher_task_published') continue
      items.value = [
        {
          id: `server-${row.id}`,
          kind: 'teacher_task_published' as const,
          title: row.title,
          body: row.body,
          createdAt: row.created_at ?? new Date().toISOString(),
          read: false,
        },
        ...items.value,
      ].slice(0, 50)
      seenSet.add(row.id)
      added = true
    }
    if (added) {
      persist(userId)
      localStorage.setItem(seenKey, JSON.stringify([...seenSet]))
    }
  }

  /** 合并管理员公告（学生端），按公告 id 去重 */
  function ingestAnnouncements(
    userId: number | string,
    announcements: Array<{ id: number; title: string; body: string; created_at: string | null }>,
  ) {
    const seenKey = `plex-notif-announce-seen:${userId}`
    let seen: number[] = []
    try {
      const raw = localStorage.getItem(seenKey)
      if (raw) seen = JSON.parse(raw) as number[]
    } catch {
      seen = []
    }
    const seenSet = new Set(seen)
    let added = false
    for (const row of announcements) {
      if (seenSet.has(row.id)) continue
      items.value = [
        {
          id: `announce-${row.id}`,
          kind: 'system_announcement' as const,
          title: row.title,
          body: row.body,
          createdAt: row.created_at ?? new Date().toISOString(),
          read: false,
        },
        ...items.value,
      ].slice(0, 50)
      seenSet.add(row.id)
      added = true
    }
    if (added) {
      persist(userId)
      localStorage.setItem(seenKey, JSON.stringify([...seenSet]))
    }
  }

  return {
    items,
    unreadCount,
    hydrate,
    push,
    ingestServer,
    ingestAnnouncements,
    markRead,
    markAllRead,
    clearForLogout,
  }
})
