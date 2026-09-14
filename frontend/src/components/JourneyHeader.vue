<script setup lang="ts">
import { useRoute } from 'vue-router'
import LeafIcon from './LeafIcon.vue'
import BlindModeToggle from './BlindModeToggle.vue'
const route = useRoute()
</script>
<template>
  <a class="skip-link" href="#main-content">Skip to main content</a>
  <header class="journey-header">
    <RouterLink class="journey-brand" to="/" aria-label="TouchGrass home"
      ><span><LeafIcon /></span>TouchGrass</RouterLink
    >
    <nav aria-label="Main navigation">
      <RouterLink to="/" :class="{ active: route.path === '/' }">Home</RouterLink>
      <RouterLink to="/explore" :class="{ active: route.path.startsWith('/explore') }"
        >Explore</RouterLink
      >
    </nav>
    <BlindModeToggle />
  </header>
</template>
<style scoped>
.journey-header {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 36px;
  padding: 0 32px;
  background: white;
  border-bottom: 1px solid #e7ebe2;
  position: relative;
  z-index: 25;
}
.journey-brand {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--tg-green-950);
  font:
    bold 1.25rem Georgia,
    serif;
}
.journey-brand span {
  width: 31px;
  height: 31px;
  display: grid;
  place-items: center;
  background: var(--tg-green-700);
  border-radius: 9px;
  color: white;
}
.journey-brand svg {
  width: 20px;
  height: 20px;
}
nav {
  display: flex;
  gap: 6px;
}
nav a {
  display: grid;
  place-items: center;
  min-height: 44px;
  padding: 0 17px;
  font-size: 0.86rem;
  font-weight: 650;
  color: var(--tg-muted);
  border-radius: 9px;
}
nav a.active,
nav a:hover {
  color: var(--tg-green-950);
  background: var(--tg-green-100);
}
@media (max-width: 540px) {
  .journey-header {
    padding: 0 18px;
    gap: 20px;
    height: 60px;
  }
  .journey-brand {
    font-size: 1.15rem;
  }
  nav a {
    padding: 0 11px;
  }
}
</style>
