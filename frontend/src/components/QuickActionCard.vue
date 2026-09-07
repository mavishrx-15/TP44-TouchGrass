<script setup lang="ts">
defineProps<{ icon: string; title: string; description: string; to: string }>()
</script>

<template>
  <RouterLink class="action-card" :to="to">
    <span class="action-icon" aria-hidden="true">{{ icon }}</span>
    <strong>{{ title }}</strong>
    <p>{{ description }}</p>
    <span class="action-link">Open <span aria-hidden="true">→</span></span>
  </RouterLink>
</template>

<style scoped>
.action-card {
  display: flex;
  min-height: 210px;
  flex-direction: column;
  padding: 24px;
  border: 1px solid var(--tg-border);
  border-radius: 15px;
  background: var(--tg-surface);
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    border-color 180ms ease;
}

.action-card:hover {
  border-color: var(--tg-green-300);
  box-shadow: var(--tg-shadow);
  transform: translateY(-3px);
}

.action-icon {
  min-height: 40px;
  font-size: 1.7rem;
}

strong {
  margin-top: 12px;
  color: var(--tg-green-950);
  font-size: 0.95rem;
}

p {
  margin: 9px 0 18px;
  color: var(--tg-muted);
  font-size: 0.78rem;
  line-height: 1.55;
}

.action-link {
  margin-top: auto;
  color: var(--tg-green-700);
  font-size: 0.78rem;
  font-weight: 800;
}
</style>
