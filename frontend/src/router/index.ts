import { createRouter, createWebHistory } from 'vue-router'
import { getAccessToken, watchAccessExpiry } from '@/api/client'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/access',
      name: 'access',
      component: () => import('@/views/AccessView.vue'),
      meta: { public: true },
    },
    {
      path: '/recommendations',
      name: 'recommendations',
      component: () => import('@/views/RecommendationsView.vue'),
    },
    {
      path: '/personalised-route',
      name: 'personalised-route',
      component: () => import('@/views/PersonalisedRouteView.vue'),
    },
    { path: '/', name: 'home', component: HomeView },
    {
      path: '/map',
      name: 'map',
      component: () => import('@/views/MapView.vue'),
    },
    {
      path: '/tree-explorer',
      name: 'tree-explorer',
      component: () => import('@/views/TreeExplorerView.vue'),
    },
    {
      path: '/tree-health',
      name: 'tree-health',
      component: () => import('@/views/TreeHealthView.vue'),
    },
    {
      path: '/identify-tree',
      name: 'identify-tree',
      component: () => import('@/views/IdentifyTreeView.vue'),
    },
  ],
  scrollBehavior() {
    return { top: 0, left: 0 }
  },
})

router.beforeEach((to) => {
  const token = getAccessToken()
  if (!to.meta.public && !token) return { name: 'access', query: { redirect: to.fullPath } }
  if (to.name === 'access' && token) return { name: 'home' }
})
window.addEventListener('access-expired', () => {
  if (router.currentRoute.value.name !== 'access') {
    void router.replace({ name: 'access', query: { redirect: router.currentRoute.value.fullPath } })
  }
})
watchAccessExpiry()
export default router
