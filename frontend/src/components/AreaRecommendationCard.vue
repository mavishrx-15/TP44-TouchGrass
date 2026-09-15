<script setup lang="ts">
import type { rankRecommendations } from '@/services/preferences'
defineProps<{ area: ReturnType<typeof rankRecommendations>[number]; rank: number }>()
const emit = defineEmits<{ choose: [] }>()
</script>
<template>
  <article class="area-recommendation">
    <header>
      <span class="eyebrow">Recommendation {{ rank }}</span>
      <h2>{{ area.label }}</h2>
      <ElTag :type="area.withinTime ? 'success' : 'warning'">{{
        area.withinTime ? 'Within estimated walking time' : 'Beyond estimated walking time'
      }}</ElTag>
    </header>
    <section>
      <h3>Area Overview</h3>
      <p>{{ area.description }}</p>
      <p>
        <strong>{{ area.distanceKm.toFixed(1) }} km</strong> from your starting location
      </p>
      <small
        >Straight-line distance · at least about {{ area.estimatedMinutes }} min on foot. Calculate
        a route for the actual walking time.</small
      >
    </section>
    <section>
      <h3>Tree Info</h3>
      <dl>
        <div>
          <dt>Recorded trees</dt>
          <dd>{{ area.treeCount }}</dd>
        </div>
        <div>
          <dt>Tree density</dt>
          <dd>{{ area.density }}</dd>
        </div>
        <div>
          <dt>Dominant genus</dt>
          <dd>{{ area.dominantGenus ?? 'Mixed / other' }}</dd>
        </div>
      </dl>
    </section>
    <section>
      <h3>Why This Area Matches</h3>
      <ul>
        <li v-for="reason in area.reasons" :key="reason">{{ reason }}</li>
      </ul>
    </section>
    <ElButton type="primary" @click="emit('choose')">Calculate route here</ElButton>
  </article>
</template>
<style scoped>
.area-recommendation {
  display: flex;
  flex-direction: column;
  padding: 26px;
  border: 1px solid var(--tg-border);
  border-radius: 20px;
  background: white;
}
h2 {
  font-family: Georgia, serif;
  color: var(--tg-green-950);
  font-size: 1.45rem;
  overflow-wrap: anywhere;
}
h3 {
  font-size: 1rem;
  color: var(--tg-green-800);
}
section {
  padding: 12px 0;
  border-bottom: 1px solid var(--tg-border);
}
p,
li,
small {
  line-height: 1.65;
}
small {
  color: var(--tg-muted);
}
ul {
  padding-left: 18px;
}
li + li {
  margin-top: 10px;
}
dl div {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 6px 0;
}
dd {
  margin: 0;
  font-weight: 700;
}
.el-button {
  margin-top: auto;
  width: 100%;
}
section:last-of-type {
  border: 0;
  margin-bottom: 16px;
}
</style>
