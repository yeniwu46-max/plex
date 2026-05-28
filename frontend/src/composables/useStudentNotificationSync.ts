import { onMounted, onUnmounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import {
  readKnownAssignmentIds,
  useNotificationStore,
  writeKnownAssignmentIds,
} from '../stores/notifications'
import { fetchStudentAssignments } from '../api/studentAssignments'
import { fetchStudentInbox } from '../api/studentInbox'

const POLL_MS = 20000

/** 学生端：服务端收件箱 + 作业列表快照 */
export function useStudentNotificationSync() {
  const auth = useAuthStore()
  const notifications = useNotificationStore()
  let pollTimer: ReturnType<typeof setInterval> | null = null

  function userId() {
    return auth.profile?.id
  }

  function initStore() {
    const id = userId()
    if (!id) return
    notifications.hydrate(id)
  }

  async function syncServerInbox() {
    const id = userId()
    if (!id || auth.profile?.role !== 'student') return
    try {
      const inbox = await fetchStudentInbox(true)
      notifications.ingestServer(id, inbox.items)
    } catch {
      /* 非关键 */
    }
  }

  async function syncTeacherAssignments() {
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
        notifications.push(id, 'teacher_task_published', {
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
  }

  function startPolling() {
    if (pollTimer) return
    pollTimer = setInterval(() => {
      void syncServerInbox()
    }, POLL_MS)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  onMounted(() => {
    initStore()
    void syncAll()
    startPolling()
  })

  onUnmounted(stopPolling)

  watch(
    () => auth.profile?.id,
    (id) => {
      if (id) {
        notifications.hydrate(id)
        void syncAll()
        startPolling()
      } else {
        stopPolling()
        notifications.clearForLogout()
      }
    },
  )

  return { syncTeacherAssignments, syncServerInbox, syncAll, initStore }
}
