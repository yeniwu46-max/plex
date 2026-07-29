import { onMounted, onUnmounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import {
  readKnownAssignmentIds,
  useNotificationStore,
  writeKnownAssignmentIds,
} from '../stores/notifications'
import { fetchStudentAssignments } from '../api/studentAssignments'
import { fetchStudentInbox } from '../api/studentInbox'
import { http, type ApiEnvelope } from '../api/http'
import type { SystemAnnouncement } from '../api/teacherAnnouncements'

async function fetchStudentAnnouncements(): Promise<SystemAnnouncement[]> {
  const { data } = await http.get<ApiEnvelope<SystemAnnouncement[]>>('/v1/student/announcements')
  if (data.code !== 0) throw new Error(data.message || '公告加载失败')
  return data.data
}

const POLL_MS = 20000

let refCount = 0
let pollTimer: ReturnType<typeof setInterval> | null = null
let profileWatchStop: (() => void) | null = null

function getAuth() {
  return useAuthStore()
}

function getNotifications() {
  return useNotificationStore()
}

function userId() {
  return getAuth().profile?.id
}

function initStore() {
  const id = userId()
  if (!id) return
  getNotifications().hydrate(id)
}

async function syncServerInbox() {
  const auth = getAuth()
  const id = userId()
  if (!id || auth.profile?.role !== 'student') return
  try {
    const inbox = await fetchStudentInbox(true)
    getNotifications().ingestServer(id, inbox.items)
  } catch {
    /* 非关键 */
  }
}

async function syncAnnouncements() {
  const auth = getAuth()
  const id = userId()
  if (!id || auth.profile?.role !== 'student') return
  try {
    const items = await fetchStudentAnnouncements()
    getNotifications().ingestAnnouncements(id, items)
  } catch {
    /* 非关键 */
  }
}

async function syncTeacherAssignments() {
  const auth = getAuth()
  const id = userId()
  if (!id || auth.profile?.role !== 'student') return

  try {
    const data = await fetchStudentAssignments()
    const pendingIds = data.items.filter((item) => item.status === 'pending').map((item) => item.id)
    const known = readKnownAssignmentIds(id)

    if (known === null) {
      writeKnownAssignmentIds(id, pendingIds)
      return
    }

    const newIds = pendingIds.filter((qid) => !known.includes(qid))
    if (newIds.length > 0) {
      const count = newIds.length
      getNotifications().push(id, 'teacher_task_published', {
        body:
          count > 1
            ? `老师发布了 ${count} 道新任务，快去今日委托查看。`
            : '老师发布了新的任务，快去今日委托或探索舱查看。',
      })
    }

    writeKnownAssignmentIds(id, pendingIds)
  } catch {
    /* 静默 */
  }
}

async function syncAll() {
  await syncServerInbox()
  await syncTeacherAssignments()
  await syncAnnouncements()
}

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(() => {
    void syncServerInbox()
    void syncAnnouncements()
  }, POLL_MS)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function ensureStarted() {
  if (refCount === 0) {
    initStore()
    void syncAll()
    startPolling()
    if (!profileWatchStop) {
      profileWatchStop = watch(
        () => getAuth().profile?.id,
        (id) => {
          if (id) {
            getNotifications().hydrate(id)
            void syncAll()
            startPolling()
          } else {
            stopPolling()
            getNotifications().clearForLogout()
          }
        },
      )
    }
  }
  refCount += 1
}

function release() {
  refCount = Math.max(0, refCount - 1)
  if (refCount === 0) {
    stopPolling()
    profileWatchStop?.()
    profileWatchStop = null
  }
}

/** 学生端：服务端收件箱 + 作业列表快照（全局单例，避免路由切换重复拉数） */
export function useStudentNotificationSync() {
  onMounted(() => {
    ensureStarted()
  })

  onUnmounted(() => {
    release()
  })

  return { syncTeacherAssignments, syncServerInbox, syncAll, initStore }
}
