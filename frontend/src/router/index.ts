import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import { getAccessToken } from '@/services/access.service'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/access', name: 'access', component: () => import('@/views/AccessView.vue') },
    { path: '/', name: 'home', component: HomeView },
    {
      path: '/explore',
      name: 'personalised-route',
      component: () => import('@/views/PersonalisedRouteView.vue'),
    },
    {
      path: '/explore/recommendations',
      name: 'recommendations',
      component: () => import('@/views/RecommendationsView.vue'),
    },
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
  const unlocked = !!getAccessToken()
  if (to.name !== 'access' && !unlocked)
    return { name: 'access', query: { redirect: to.fullPath }, replace: true }
  if (to.name === 'access' && unlocked) return { name: 'home', replace: true }
})

export default router
