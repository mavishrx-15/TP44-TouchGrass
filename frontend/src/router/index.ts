import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import AccessView from '@/views/AccessView.vue'
import { getAccessToken } from '@/api/client'

// One route for now. Add a route per user story as views are built.
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: HomeView, meta: { requiresAccess: true } },
    { path: '/access', name: 'access', component: AccessView },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAccess && !getAccessToken()) {
    return { name: 'access' }
  }
  if (to.name === 'access' && getAccessToken()) {
    return { name: 'home' }
  }
})

export default router
