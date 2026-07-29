import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    // 同壳内切页：保持滚动位置感知更轻，仅跨页回到顶部
    if (to.path !== from.path) return { top: 0 }
    return undefined
  },
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
      path: '/register',
      name: 'register',
      meta: { public: true },
      component: () => import('../views/RegisterView.vue'),
    },
    {
      path: '/oauth/callback',
      name: 'oauth-callback',
      meta: { public: true },
      component: () => import('../views/OAuthCallbackView.vue'),
    },
    {
      path: '/student',
      meta: { roles: ['student'] },
      component: () => import('../layouts/StudentShellLayout.vue'),
      children: [
        {
          path: '',
          name: 'student-home',
          component: () => import('../views/StudentHomeView.vue'),
        },
        {
          path: 'discovery',
          name: 'student-discovery',
          component: () => import('../views/DiscoveryCabinView.vue'),
        },
        {
          path: 'star-path',
          name: 'student-star-path-lab',
          component: () => import('../views/StarPathLabView.vue'),
        },
        {
          path: 'star-path/resources',
          name: 'student-star-path-resources',
          component: () => import('../views/StudentResourcesView.vue'),
        },
        {
          path: 'trials',
          name: 'student-trials',
          component: () => import('../views/StudentTrialView.vue'),
        },
        {
          path: 'trials/practice/:questionId',
          name: 'student-trial-practice',
          component: () => import('../views/StudentTrialPracticeView.vue'),
        },
        {
          path: 'messenger',
          name: 'student-messenger',
          component: () => import('../views/MessengerView.vue'),
        },
        { path: 'me', redirect: '/student/me/growth' },
        {
          path: 'me/growth',
          name: 'student-growth',
          component: () => import('../views/StudentGrowthView.vue'),
        },
        {
          path: 'me/profile',
          name: 'student-profile',
          component: () => import('../views/StudentProfileView.vue'),
        },
        {
          path: 'me/settings',
          name: 'student-settings',
          component: () => import('../views/StudentControlView.vue'),
        },
        { path: 'daily', redirect: { path: '/student', hash: '#daily' } },
        { path: 'archives', redirect: '/student/me/growth' },
        { path: 'profile', redirect: '/student/me/growth' },
        { path: 'control', redirect: '/student/me/settings' },
        { path: 'resources', redirect: '/student/star-path/resources' },
      ],
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
        { path: 'explorers', redirect: '/teacher/starfield' },
        {
          path: 'classes',
          name: 'teacher-classes',
          component: () => import('../views/TeacherClassManageView.vue'),
        },
        {
          path: 'trials',
          name: 'teacher-trials',
          component: () => import('../views/TrialArenaView.vue'),
        },
        {
          path: 'trials/create',
          name: 'teacher-trial-create',
          component: () => import('../views/TeacherTrialCreateView.vue'),
        },
        {
          path: 'resources',
          name: 'teacher-resource-review',
          component: () => import('../views/TeacherResourceReviewView.vue'),
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
      redirect: { path: '/student', hash: '#daily' },
    },
    {
      path: '/archives',
      redirect: '/student/me/growth',
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
    if ((to.name === 'login' || to.name === 'register') && auth.isAuthenticated) {
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
