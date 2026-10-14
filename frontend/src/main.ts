import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/tokens.css'
import './styles/global.css'

createApp(App).use(createPinia()).use(router).mount('#app')

/* Temporarily disabled with the shared-password gate in router/index.ts.
window.addEventListener('touchgrass:access-expired', () => {
  if (router.currentRoute.value.name !== 'access')
    void router.replace({ name: 'access', query: { redirect: router.currentRoute.value.fullPath } })
})
*/
