import { onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useTeacherNotificationStore } from '../stores/teacherNotifications'
import { fetchTeacherAnnouncements } from '../api/teacherAnnouncements'

export function useTeacherNotificationSync() {
  const auth = useAuthStore()
  const notifications = useTeacherNotificationStore()

  function userId() {
    return auth.profile?.id
  }

  function isTeacherRole() {
    const role = auth.profile?.role
    return role === 'teacher' || role === 'admin'
  }

  function initStore() {
    const id = userId()
    if (!id) return
    notifications.hydrate(id)
  }

  async function syncAnnouncements() {
    const id = userId()
    if (!id || !isTeacherRole()) return
    try {
      const list = await fetchTeacherAnnouncements()
      notifications.syncAdminAnnouncements(id, list)
    } catch {
      /* 非关键 */
    }
  }

  onMounted(() => {
    initStore()
    void syncAnnouncements()
  })

  watch(
    () => auth.profile?.id,
    (id) => {
      if (id && isTeacherRole()) {
        notifications.hydrate(id)
        void syncAnnouncements()
      } else {
        notifications.clearForLogout()
      }
    },
  )

  return { syncAnnouncements, initStore }
}
