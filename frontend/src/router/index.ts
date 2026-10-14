import { createRouter, createWebHistory } from 'vue-router'
// Temporarily disabled access gate. Restore with the guard below.
// import { getAccessToken, watchAccessExpiry } from '@/api/client'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // { path: '/access', name: 'access', component: () => import('@/views/AccessView.vue') },
    { path: '/access', redirect: '/' },
    { path: '/', name: 'home', component: HomeView },
    { path: '/walk', name: 'walk', component: () => import('@/views/WalkView.vue') },
    { path: '/rewards', name: 'rewards', component: () => import('@/views/RewardsView.vue') },
    // Explore and its sub-pages are gone; an old link to one lands on Home
    // instead of a blank unmatched-route page.
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior() {
    return { top: 0, left: 0 }
  },
})

/* Temporarily disabled: shared-password gate and expiry redirects.
router.beforeEach((to) => {
  const unlocked = !!getAccessToken()
  if (to.name !== 'access' && !unlocked)
    return { name: 'access', query: { redirect: to.fullPath }, replace: true }
  if (to.name === 'access' && unlocked) return { name: 'home', replace: true }
})
window.addEventListener('access-expired', () => {
  if (router.currentRoute.value.name !== 'access') {
    void router.replace({ name: 'access', query: { redirect: router.currentRoute.value.fullPath } })
  }
})
watchAccessExpiry()
*/

export default router
