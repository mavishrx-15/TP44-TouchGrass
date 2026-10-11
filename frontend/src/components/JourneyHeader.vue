<template>
  <a class="skip-link" href="#main-content">Skip to main content</a>
  <header class="journey-header">
    <RouterLink class="journey-brand" to="/" aria-label="TouchGrass Melbourne home"
      ><img src="/touchgrass-mark.svg" alt="" />
      <span class="brand-name"
        ><strong>TouchGrass</strong><small>Melbourne</small></span
      ></RouterLink
    >
    <div class="header-actions">
      <RouterLink class="rewards-link" to="/rewards">Leaf rewards</RouterLink>
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
  gap: 16px;
  flex-shrink: 0;
  background: white;
  border-bottom: 1px solid #e7ebe2;
  position: relative;
  z-index: 25;
}
.journey-brand {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-shrink: 0;
  text-decoration: none;
  color: var(--tg-green-950);
  font:
    700 1.35rem Georgia,
    serif;
}
.journey-brand img {
  width: 42px;
  height: 42px;
  display: block;
  object-fit: contain;
  flex-shrink: 0;
}
.brand-name {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
  line-height: 1;
}
.brand-name strong {
  font: inherit;
  font-weight: 700;
}
.brand-name small {
  color: var(--tg-green-950);
  letter-spacing: 0.03em;
  font:
    700 0.75rem/1 Georgia,
    serif;
}
@media (max-width: 540px) {
  .journey-header {
    padding: 0 18px;
    height: 60px;
  }
  .journey-brand {
    font-size: 1.25rem;
  }
}
@media (max-width: 380px) {
  .journey-header {
    padding: 0 12px;
    gap: 8px;
  }
  .journey-brand {
    font-size: 1rem;
    gap: 6px;
  }
  .journey-brand img {
    width: 34px;
    height: 34px;
  }
  .header-actions {
    gap: 6px;
  }
  .rewards-link {
    font-size: 0.7rem;
  }
}
</style>
