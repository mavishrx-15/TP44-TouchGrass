<script setup lang="ts">
import { Location } from '@element-plus/icons-vue'
import type { TreeZone } from '@/types/discovery'

defineProps<{ zone: TreeZone }>()
</script>

<template>
  <article class="zone-card">
    <header class="zone-header" :class="`density-${zone.density.toLowerCase()}`">
      <div>
        <span>Tree-dense zone</span>
        <h3>{{ zone.label }}</h3>
      </div>
      <ElTag round effect="dark" type="success">{{ zone.distanceKm.toFixed(1) }} km away</ElTag>
    </header>

    <div class="zone-content">
      <div class="zone-tags">
        <ElTag size="small" round type="success" effect="light">{{ zone.treeCount }} trees</ElTag>
        <ElTag
          size="small"
          round
          :type="
            zone.density === 'High' ? 'success' : zone.density === 'Medium' ? 'warning' : 'info'
          "
          effect="dark"
        >
          {{ zone.density }} density
        </ElTag>
        <ElTag size="small" round effect="plain">{{ zone.dominantGenus }}</ElTag>
      </div>
      <p>{{ zone.description }}</p>
      <RouterLink :to="{ path: '/map', query: { zone: zone.id } }">
        <ElButton type="primary" size="small" :icon="Location">View Zone on Map</ElButton>
      </RouterLink>
    </div>
  </article>
</template>

<style scoped>
.zone-card {
  overflow: hidden;
  border: 1px solid var(--tg-green-300);
  border-radius: 16px;
  background: var(--tg-surface);
  transition:
    transform 180ms ease,
    box-shadow 180ms ease;
}

.zone-card:hover {
  box-shadow: var(--tg-shadow);
  transform: translateY(-3px);
}

.zone-header {
  display: flex;
  min-height: 94px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px;
  background: var(--tg-green-800);
  color: white;
}

.zone-header.density-medium {
  background: #559746;
}

.zone-header span {
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

.zone-header h3 {
  margin: 8px 0 0;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.1rem;
}

.zone-header .el-tag {
  flex: none;
  border-color: rgb(255 255 255 / 15%);
  background: rgb(255 255 255 / 16%);
}

.zone-content {
  padding: 20px;
}

.zone-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.zone-content p {
  min-height: 58px;
  margin: 14px 0 18px;
  color: var(--tg-muted);
  font-size: 0.78rem;
  line-height: 1.6;
}

.zone-content .el-button {
  font-weight: 700;
}

@media (max-width: 420px) {
  .zone-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
