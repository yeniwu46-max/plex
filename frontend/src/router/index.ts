import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: () => {
        const auth = useAuthStore()
        return auth.isAuthenticated ? auth.homePathForRole(auth.profile?.role) : '/login'
      },
    },
    {
      path: '/login',
      name: 'login',
      meta: { public: true },
      component: () => import('../views/LoginView.vue'),
    },
    {
      path: '/student',
      name: 'student-home',
      meta: { roles: ['student'] },
      component: () => import('../views/StudentHomeView.vue'),
    },
    {
      path: '/student/control',
      name: 'student-control',
      meta: { roles: ['student'] },
      component: () => import('../views/StudentControlView.vue'),
    },
    {
      path: '/student/discovery',
      name: 'student-discovery',
      meta: { roles: ['student'] },
      component: () => import('../views/DiscoveryCabinView.vue'),
    },
    {
      path: '/student/star-path',
      name: 'student-star-path-lab',
      meta: { roles: ['student'] },
      component: () => import('../views/StarPathLabView.vue'),
    },
    {
      path: '/student/trials',
      name: 'student-trials',
      meta: { roles: ['student'] },
      component: () => import('../views/StudentTrialView.vue'),
    },
    {
      path: '/student/messenger',
      name: 'student-messenger',
      meta: { roles: ['student'] },
      component: () => import('../views/MessengerView.vue'),
    },
    {
      path: '/student/daily',
      name: 'student-daily-quest',
      meta: { roles: ['student'] },
      component: () => import('../views/DailyQuestView.vue'),
    },
    {
      path: '/student/archives',
      name: 'student-archives',
      meta: { roles: ['student'] },
      component: () => import('../views/ExplorationArchivesView.vue'),
    },
    {
      path: '/teacher',
      meta: { roles: ['teacher', 'admin'] },
      component: () => import('../layouts/TeacherOverviewLayout.vue'),
      children: [
        {
          path: '',
          name: 'teacher-home',
          component: () => import('../views/TeacherHomeView.vue'),
        },
        {
          path: 'starfield',
          name: 'teacher-starfield',
          component: () => import('../views/TeacherStarfieldView.vue'),
        },
        {
          path: 'explorers',
          name: 'teacher-explorers',
          component: () => import('../views/TeacherExplorersView.vue'),
        },
        {
          path: 'trials',
          name: 'teacher-trials',
          component: () => import('../views/TrialArenaView.vue'),
        },
      ],
    },
    {
      path: '/admin',
      name: 'admin-home',
      meta: { roles: ['admin'] },
      component: () => import('../views/AdminHomeView.vue'),
    },
    {
      path: '/discovery',
      redirect: '/student/discovery',
    },
    {
      path: '/star-path',
      redirect: '/student/star-path',
    },
    {
      path: '/trial-arena',
      redirect: () => {
        const auth = useAuthStore()
        const role = auth.profile?.role
        return role === 'teacher' || role === 'admin' ? '/teacher/trials' : '/student/trials'
      },
    },
    {
      path: '/messenger',
      redirect: '/student/messenger',
    },
    {
      path: '/daily',
      redirect: '/student/daily',
    },
    {
      path: '/archives',
      redirect: '/student/archives',
    },
  ],
})

function roleAllowed(required: string[] | undefined, role?: string) {
  if (!required?.length) return true
  if (!role) return false
  if (required.includes(role)) return true
  if (role === 'admin' && required.includes('teacher')) return true
  return false
}

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (to.name === 'login' && auth.isAuthenticated) {
      return auth.homePathForRole(auth.profile?.role)
    }
    return true
  }
  if (!auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  const required = to.matched
    .map((record) => record.meta.roles as string[] | undefined)
    .filter(Boolean)
    .flat() as string[] | undefined
  const uniqueRequired = required?.length ? [...new Set(required)] : undefined

  if (!roleAllowed(uniqueRequired, auth.profile?.role)) {
    return auth.homePathForRole(auth.profile?.role)
  }

  return true
})

export default router
