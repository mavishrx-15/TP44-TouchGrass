<script setup lang="ts">
import type { RouteOption } from '@/types/discovery'
defineProps<{ route: RouteOption }>()
</script>
<template>
  <article class="personal-route-card" aria-label="Recommended route">
    <ElTag :type="route.bestMatch ? 'success' : 'warning'">{{
      route.bestMatch ? 'Best available match' : 'Closest available match'
    }}</ElTag>
    <h2>{{ route.label }}</h2>
    <p>
      <strong>{{ route.durationMinutes }} min</strong> · {{ route.distanceKm.toFixed(1) }} km ·
      {{ route.treeCount }} zone trees
    </p>
    <p role="status">{{ route.message }}</p>
    <section aria-label="Why This Route?">
      <h3>Why This Route?</h3>
      <ul>
        <li v-for="reason in route.explanation" :key="reason">{{ reason }}</li>
      </ul>
    </section>
  </article>
</template>
<style scoped>
.personal-route-card {
  padding: 22px;
  border-radius: 16px;
  border: 1px solid var(--tg-border);
  background: var(--tg-green-50);
}
h2 {
  font-family: Georgia, serif;
  color: var(--tg-green-950);
}
p,
li {
  line-height: 1.6;
}
ul {
  padding-left: 20px;
}
li + li {
  margin-top: 8px;
}
</style>
