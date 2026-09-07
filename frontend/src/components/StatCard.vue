<script setup lang="ts">
defineProps<{
  icon: string
  value: string
  label: string
  detail: string
  neutral?: boolean
}>()
</script>

<template>
  <article class="stat-card" :class="{ neutral }">
    <span class="stat-icon" aria-hidden="true">{{ icon }}</span>
    <strong>{{ value }}</strong>
    <span class="stat-label">{{ label }}</span>
    <small>{{ detail }}</small>
  </article>
</template>

<style scoped>
.stat-card {
  display: grid;
  min-height: 138px;
  align-content: start;
  padding: 21px;
  border: 1px solid #b9d99e;
  border-radius: 13px;
  background: var(--tg-green-100);
}

.stat-card.neutral {
  border-color: #dacfb7;
  background: #fbf9f3;
}

.stat-icon {
  min-height: 25px;
  font-size: 1.25rem;
}

strong {
  margin-top: 4px;
  color: var(--tg-green-950);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.8rem;
  line-height: 1;
}

.stat-label {
  margin-top: 6px;
  color: var(--tg-text);
  font-size: 0.82rem;
  font-weight: 800;
}

small {
  margin-top: 5px;
  color: var(--tg-muted);
  font-size: 0.7rem;
}
</style>
