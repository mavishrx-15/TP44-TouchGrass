<script setup lang="ts">
import { onMounted, ref } from 'vue'
import JourneyHeader from '@/components/JourneyHeader.vue'
import DemoNotice from '@/components/DemoNotice.vue'
import SproutGuide from '@/components/sprout/SproutGuide.vue'
import { useJourneyStore } from '@/stores/journey'

const journey = useJourneyStore()
const initError = ref('')
async function initialize() {
  initError.value = ''
  try {
    await journey.initialize()
  } catch {
    initError.value = 'We couldn’t load covered areas. Please try again.'
  }
}
onMounted(initialize)
</script>

<template>
  <div class="home-shell">
    <JourneyHeader />
    <DemoNotice />
    <main id="main-content" tabindex="-1" class="home-page">
      <p v-if="initError" class="form-error" role="alert">
        {{ initError }}
        <button type="button" class="text-button" @click="initialize">Retry</button>
      </p>
      <SproutGuide />
    </main>
  </div>
</template>

<style scoped>
.home-shell {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
}
.home-shell :deep(.journey-header),
.home-shell :deep(.demo-notice) {
  flex-shrink: 0;
}
.home-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
@media (min-width: 801px) {
  .home-shell:has(.map-mode) {
    height: 100dvh;
    overflow: hidden;
  }
}
.form-error {
  color: #b44235;
  font-size: 0.82rem;
  margin: 10px 32px 0;
}
.text-button {
  background: none;
  border: none;
  color: var(--tg-green-700);
  font-weight: 700;
  font-size: 0.78rem;
  cursor: pointer;
}
</style>
