<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'

defineProps<{
  eyebrow: string
  title: string
  description: string
  icon: string
}>()
</script>

<template>
  <main class="feature-page">
    <div class="feature-orb orb-one" />
    <div class="feature-orb orb-two" />
    <section class="page-container feature-content">
      <span class="feature-icon" aria-hidden="true">{{ icon }}</span>
      <p class="eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p class="description">{{ description }}</p>
      <ElTag round type="success" effect="light">Coming in Epic 1 &amp; 2</ElTag>
      <RouterLink to="/">
        <ElButton class="back-button" :icon="ArrowLeft">Back to Home</ElButton>
      </RouterLink>
    </section>
  </main>
</template>

<style scoped>
.feature-page {
  position: relative;
  display: grid;
  min-height: calc(100vh - 68px);
  overflow: hidden;
  place-items: center;
  background: linear-gradient(145deg, var(--tg-cream), var(--tg-green-50));
}

.feature-content {
  position: relative;
  z-index: 1;
  padding-block: 80px;
  text-align: center;
}

.feature-icon {
  display: grid;
  width: 76px;
  height: 76px;
  margin: 0 auto 24px;
  place-items: center;
  border: 1px solid var(--tg-green-300);
  border-radius: 22px;
  background: white;
  box-shadow: var(--tg-shadow);
  font-size: 2.2rem;
}

.eyebrow {
  margin: 0 0 12px;
  color: var(--tg-green-700);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  color: var(--tg-green-950);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  letter-spacing: -0.035em;
}

.description {
  max-width: 570px;
  margin: 20px auto 24px;
  color: var(--tg-muted);
  font-size: 1rem;
  line-height: 1.7;
}

.back-button {
  display: flex;
  margin: 30px auto 0;
}

.feature-orb {
  position: absolute;
  border-radius: 50%;
  background: var(--tg-green-100);
}

.orb-one {
  width: 360px;
  height: 360px;
  top: -190px;
  right: -80px;
}

.orb-two {
  width: 240px;
  height: 240px;
  bottom: -130px;
  left: -80px;
}
</style>
