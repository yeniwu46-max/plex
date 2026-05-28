import { createRouter, createWebHashHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import PageView from '../views/PageView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/p/:pageId', name: 'page', component: PageView, props: true },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
