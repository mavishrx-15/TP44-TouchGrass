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
  <JourneyHeader />
  <DemoNotice />
  <main id="main-content" tabindex="-1" class="home-page">
    <p v-if="initError" class="form-error" role="alert">
      {{ initError }}
      <button type="button" class="text-button" @click="initialize">Retry</button>
    </p>
    <SproutGuide />
  </main>
</template>

<style scoped>
.home-page {
  min-height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
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
