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
      component: () => import('../views/StudentHomeView.vue'),
    },
    {
      path: '/teacher',
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
      ],
    },
    {
      path: '/admin',
      name: 'admin-home',
      component: () => import('../views/AdminHomeView.vue'),
    },
    {
      path: '/discovery',
      name: 'discovery',
      component: () => import('../views/DiscoveryCabinView.vue'),
    },
    {
      path: '/star-path',
      name: 'star-path-lab',
      component: () => import('../views/StarPathLabView.vue'),
    },
    {
      path: '/trial-arena',
      name: 'trial-arena',
      component: () => import('../views/TrialArenaView.vue'),
    },
    {
      path: '/messenger',
      name: 'messenger',
      component: () => import('../views/MessengerView.vue'),
    },
    {
      path: '/daily',
      name: 'daily-quest',
      component: () => import('../views/DailyQuestView.vue'),
    },
    {
      path: '/archives',
      name: 'archives',
      component: () => import('../views/ExplorationArchivesView.vue'),
    },
  ],
})

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
  return true
})

export default router
