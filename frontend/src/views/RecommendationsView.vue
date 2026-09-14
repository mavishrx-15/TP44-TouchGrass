<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import JourneyHeader from '@/components/JourneyHeader.vue'
import DemoNotice from '@/components/DemoNotice.vue'
import RecommendationCard from '@/components/RecommendationCard.vue'
import { useJourneyStore } from '@/stores/journey'
import { useAccessibilityStore } from '@/stores/accessibility'
import type { Recommendation } from '@/types/personalisation'
const journey = useJourneyStore()
const accessibility = useAccessibilityStore()
const router = useRouter()
const navigating = ref<string | null>(null)
async function navigate(area: Recommendation) {
  if (navigating.value) return
  navigating.value = area.id
  journey.destination = { id: area.id, label: area.label, coordinates: area.center }
  journey.travelMode = 'WALK'
  await router.push('/explore')
}
onMounted(async () => {
  if (journey.startLocation) await journey.refreshAreas()
})
watch(
  () => journey.recommendations,
  (list) => {
    if (!list.length) return
    const best = list[0]!
    accessibility.speak(
      `Found ${Math.min(3, list.length)} areas. Best match: ${best.label}. ${best.match.sentence}`,
    )
  },
)
</script>
<template>
  <JourneyHeader /><DemoNotice />
  <main id="main-content" tabindex="-1" class="recommendations-page">
    <RouterLink class="back-link" to="/explore">‹ &nbsp; Back to your route</RouterLink>
    <header class="recommendations-heading">
      <span class="eyebrow"
        >{{ journey.coverage?.precinct.name ?? 'Explore your surroundings'
        }}<template v-if="journey.preferences.walkingTime">
          ·
          {{
            journey.preferences.walkingTime === 20
              ? '20+ min walk'
              : `Within ${journey.preferences.walkingTime} min`
          }}</template
        ></span
      >
      <h1>Areas that match how you want to feel</h1>
      <p>
        Ranked using the tree canopy, noise, allergy and time preferences you set on Home — every
        card below shows its full detail, so you can compare all three without clicking through.
      </p>
    </header>
    <div v-if="!journey.startLocation" class="recommendations-empty">
      <h2>Let’s find your starting point.</h2>
      <p>Choose a location on Home to see areas near you.</p>
      <RouterLink class="primary-button" to="/">Choose starting location →</RouterLink>
    </div>
    <div
      v-else-if="journey.areasLoading"
      class="recommendations-grid"
      aria-busy="true"
      aria-label="Loading recommended areas"
    >
      <div v-for="n in 3" :key="n" class="skeleton-card">
        <div />
        <div />
        <div />
        <p v-if="n === 1" role="status">Finding areas that fit your preferences…</p>
      </div>
    </div>
    <div v-else-if="journey.areaError" class="recommendations-empty" role="alert">
      <h2>We couldn’t load areas just now.</h2>
      <p>{{ journey.areaError }}</p>
      <button class="primary-button" @click="journey.refreshAreas">Try again</button>
    </div>
    <template v-else-if="journey.recommendations.length">
      <p v-if="journey.coverage?.outside" class="notice">
        Showing areas in {{ journey.coverage.precinct.name }}, your nearest covered precinct,
        {{ journey.coverage.distanceKm.toFixed(1) }} km from your starting point.
      </p>
      <p class="mobile-card-count">
        {{ Math.min(3, journey.recommendations.length) }} areas to compare · Full details on every
        card
      </p>
      <div class="recommendations-grid">
        <RecommendationCard
          v-for="(area, index) in journey.recommendations.slice(0, 3)"
          :key="area.id"
          :area="area"
          :best="index === 0"
          :busy="navigating === area.id"
          @navigate="navigate(area)"
        />
      </div>
    </template>
    <div v-else class="recommendations-empty">
      <h2>No areas found here yet.</h2>
      <p>Try another starting point to explore a different covered area.</p>
      <RouterLink class="primary-button" to="/">Update Preferences</RouterLink>
    </div>
  </main>
</template>
<style scoped>
.recommendations-page {
  width: min(1380px, calc(100% - 64px));
  margin: 0 auto;
  padding: 28px 0 48px;
}
.back-link {
  display: inline-block;
  color: var(--tg-muted);
  font-size: 0.78rem;
  padding: 8px 0;
  margin-bottom: 10px;
}
.back-link:hover {
  color: var(--tg-green-800);
}
.recommendations-heading h1 {
  font:
    bold clamp(1.6rem, 2.5vw, 2rem)/1.15 Georgia,
    serif;
  margin: 8px 0 10px;
  color: var(--tg-green-950);
}
.recommendations-heading > p {
  font-size: 0.82rem;
  color: var(--tg-muted);
  line-height: 1.6;
  max-width: 670px;
  margin: 0 0 26px;
}
.recommendations-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
  align-items: start;
}
.recommendations-empty {
  text-align: center;
  max-width: 480px;
  margin: 55px auto;
  padding: 30px;
  background: white;
  border: 1px solid var(--tg-border);
  border-radius: 18px;
}
.recommendations-empty h2 {
  font:
    bold 1.5rem Georgia,
    serif;
}
.recommendations-empty p {
  font-size: 0.9rem;
  color: var(--tg-muted);
  line-height: 1.6;
}
.mobile-card-count {
  display: none;
}
.skeleton-card {
  height: 490px;
  padding: 22px;
  border: 1px solid var(--tg-border);
  border-radius: 14px;
  background: white;
}
.skeleton-card > div {
  background: #ecf0e6;
  border-radius: 10px;
  height: 32px;
  margin-bottom: 18px;
  animation: pulse 1.5s ease-in-out infinite;
}
.skeleton-card > div:nth-child(2) {
  height: 120px;
}
.skeleton-card > div:nth-child(3) {
  height: 180px;
}
.skeleton-card p {
  color: var(--tg-muted);
  font-size: 0.8rem;
}
@keyframes pulse {
  50% {
    opacity: 0.45;
  }
}
@media (max-width: 1000px) and (min-width: 761px) {
  .recommendations-page {
    width: calc(100% - 32px);
  }
  .recommendations-grid {
    gap: 12px;
  }
}
@media (max-width: 760px) {
  .recommendations-page {
    width: calc(100% - 36px);
    padding-top: 19px;
  }
  .recommendations-heading > p {
    font-size: 0.8rem;
    margin-bottom: 15px;
  }
  .recommendations-grid {
    grid-template-columns: 1fr;
    gap: 18px;
  }
  .mobile-card-count {
    display: block;
    font-size: 0.75rem;
    color: var(--tg-muted);
    margin: 0 0 16px;
  }
  .recommendations-empty {
    margin-top: 30px;
    padding: 24px;
  }
}
</style>
