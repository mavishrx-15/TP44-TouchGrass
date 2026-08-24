<script setup lang="ts">
import { Location } from '@element-plus/icons-vue'

defineProps<{
  name: string
  distance: string
  trees: string
  density: 'High density' | 'Medium density'
  description: string
  scene: 'park' | 'river' | 'garden'
}>()
</script>

<template>
  <article class="place-card">
    <div
      class="place-visual"
      :class="`scene-${scene}`"
      role="img"
      :aria-label="`${name} landscape`"
    >
      <span class="sun" />
      <span class="hill hill-back" />
      <span class="hill hill-front" />
      <span v-if="scene === 'river'" class="river" />
    </div>
    <div class="place-content">
      <div class="place-heading">
        <h3>{{ name }}</h3>
        <ElTag size="small" round type="success" effect="light">{{ distance }}</ElTag>
      </div>
      <div class="place-tags">
        <ElTag size="small" round type="success" effect="light">🌳 {{ trees }} trees</ElTag>
        <ElTag
          size="small"
          round
          :type="density === 'High density' ? 'success' : 'warning'"
          effect="dark"
        >
          {{ density }}
        </ElTag>
      </div>
      <p>{{ description }}</p>
      <RouterLink to="/map">
        <ElButton type="primary" size="small" :icon="Location">View on Map</ElButton>
      </RouterLink>
    </div>
  </article>
</template>

<style scoped>
.place-card {
  overflow: hidden;
  border: 1px solid var(--tg-border);
  border-radius: 16px;
  background: var(--tg-surface);
  transition:
    transform 180ms ease,
    box-shadow 180ms ease;
}

.place-card:hover {
  box-shadow: var(--tg-shadow);
  transform: translateY(-3px);
}

.place-visual {
  position: relative;
  height: 170px;
  overflow: hidden;
  background: linear-gradient(#b9d9c2 0 50%, #729c52 50%);
}

.scene-river {
  background: linear-gradient(#b9d7d1 0 48%, #6d994f 48%);
}

.scene-garden {
  background: linear-gradient(#d5dfbd 0 48%, #7da05b 48%);
}

.sun {
  position: absolute;
  width: 38px;
  height: 38px;
  top: 24px;
  right: 36px;
  border-radius: 50%;
  background: rgb(255 241 174 / 82%);
}

.hill {
  position: absolute;
  border-radius: 50% 50% 0 0;
}

.hill-back {
  width: 110%;
  height: 85px;
  right: -35%;
  bottom: 20px;
  background: #527d41;
  transform: rotate(-7deg);
}

.hill-front {
  width: 120%;
  height: 90px;
  bottom: -35px;
  left: -38%;
  background: #2f6638;
  transform: rotate(7deg);
}

.river {
  position: absolute;
  z-index: 2;
  width: 120%;
  height: 38px;
  right: -38%;
  bottom: 4px;
  border-radius: 50%;
  background: #7bb8c0;
  transform: rotate(-10deg);
}

.place-content {
  padding: 20px;
}

.place-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

h3 {
  margin: 0;
  color: var(--tg-green-950);
  font-size: 1rem;
}

.place-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

p {
  min-height: 58px;
  margin: 13px 0 17px;
  color: var(--tg-muted);
  font-size: 0.77rem;
  line-height: 1.55;
}

.el-button {
  font-weight: 700;
}
</style>
