import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import type { SearchScope } from '../types/globalSearch'

/**
 * Derives the current search scope from the route path and user role.
 * Admin users on /admin → admin scope
 * Teacher/admin on /teacher/* → teacher scope
 * Everything else → student scope
 */
export function useSearchScope() {
  const route = useRoute()
  const auth = useAuthStore()

  const scope = computed<SearchScope>(() => {
    const path = route.path
    const role = auth.profile?.role

    if (path.startsWith('/admin') && role === 'admin') return 'admin'
    if (path.startsWith('/teacher') && (role === 'teacher' || role === 'admin')) return 'teacher'
    return 'student'
  })

  return scope
}
