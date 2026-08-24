import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
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

export default router
