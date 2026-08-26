<script setup lang="ts">
import { Menu, Search } from '@element-plus/icons-vue'
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const mobileMenuOpen = ref(false)
const route = useRoute()

const navigation = [
  { label: 'Home', to: '/' },
  { label: 'Map', to: '/map' },
  { label: 'Tree Explorer', to: '/tree-explorer' },
  { label: 'Tree Health', to: '/tree-health' },
]

function goHome() {
  if (route.path === '/') window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <header class="app-header">
    <div class="page-container header-inner">
      <RouterLink class="brand" to="/" aria-label="TouchGrass home" @click="goHome">
        <span class="brand-mark" aria-hidden="true" />
        <span>TouchGrass</span>
      </RouterLink>

      <nav class="desktop-nav" aria-label="Main navigation">
        <RouterLink
          v-for="item in navigation"
          :key="item.label"
          :to="item.to"
          @click="item.to === '/' && goHome()"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <RouterLink class="identify-link" to="/identify-tree">
        <ElButton class="identify-button" plain :icon="Search">Identify a Tree</ElButton>
      </RouterLink>
      <ElButton
        class="menu-button"
        text
        :icon="Menu"
        aria-label="Open navigation"
        @click="mobileMenuOpen = true"
      />
    </div>

    <ElDrawer v-model="mobileMenuOpen" title="TouchGrass" size="min(82vw, 320px)">
      <nav class="mobile-nav" aria-label="Mobile navigation">
        <RouterLink
          v-for="item in navigation"
          :key="item.label"
          :to="item.to"
          @click="mobileMenuOpen = false"
        >
          {{ item.label }}
        </RouterLink>
        <RouterLink to="/identify-tree" @click="mobileMenuOpen = false">
          <ElButton type="primary" :icon="Search">Identify a Tree</ElButton>
        </RouterLink>
      </nav>
    </ElDrawer>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  z-index: 20;
  top: 0;
  border-bottom: 1px solid rgb(23 53 29 / 10%);
  background: rgb(255 255 255 / 94%);
  backdrop-filter: blur(12px);
}

.header-inner {
  display: flex;
  min-height: 68px;
  align-items: center;
  gap: 28px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--tg-green-950);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.1rem;
  font-weight: 700;
}

.brand-mark {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 9px;
  background: var(--tg-green-700);
}

.desktop-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.desktop-nav a {
  padding: 9px 13px;
  border-radius: 9px;
  color: var(--tg-muted);
  font-size: 0.88rem;
  font-weight: 600;
}

.desktop-nav a:hover,
.desktop-nav a.router-link-active {
  background: var(--tg-green-100);
  color: var(--tg-green-950);
}

.identify-link {
  margin-left: auto;
}

.menu-button {
  display: none;
  margin-left: auto;
  font-size: 1.25rem;
}

.mobile-nav {
  display: grid;
  gap: 8px;
}

.mobile-nav a {
  padding: 12px;
  border-radius: 8px;
  color: var(--tg-text);
  font-weight: 600;
}

.mobile-nav a:hover {
  background: var(--tg-green-100);
}

@media (max-width: 780px) {
  .desktop-nav,
  .identify-link {
    display: none;
  }

  .menu-button {
    display: inline-flex;
  }
}
</style>
