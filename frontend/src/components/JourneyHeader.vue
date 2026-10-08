<script setup lang="ts">
import LeafIcon from './LeafIcon.vue'
import BlindModeToggle from './BlindModeToggle.vue'
</script>
<template>
  <a class="skip-link" href="#main-content">Skip to main content</a>
  <header class="journey-header">
    <RouterLink class="journey-brand" to="/" aria-label="TouchGrass home"
      ><span><LeafIcon /></span>TouchGrass</RouterLink
    >
    <div class="header-actions">
      <RouterLink class="rewards-link" to="/rewards">Leaf rewards</RouterLink><BlindModeToggle />
    </div>
  </header>
</template>
<style scoped>
.header-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}
.rewards-link {
  color: #1f5a2c;
  font-size: 0.8rem;
  font-weight: 700;
}
@media (max-width: 640px) {
  .header-actions {
    gap: 10px;
  }
  .header-actions :deep(.look-picker) {
    display: none;
  }
}
.journey-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
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
@media (max-width: 540px) {
  .journey-header {
    padding: 0 18px;
    height: 60px;
  }
  .journey-brand {
    font-size: 1.15rem;
  }
}
</style>
