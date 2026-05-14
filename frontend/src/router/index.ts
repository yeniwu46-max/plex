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
      name: 'teacher-home',
      component: () => import('../views/TeacherHomeView.vue'),
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
