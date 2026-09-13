<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AreaRecommendationCard from '@/components/AreaRecommendationCard.vue'
import { getPrecinctZones } from '@/services/discovery.service'
import { rankRecommendations } from '@/services/preferences'
import { useJourneyStore } from '@/stores/journey'
import type { TreeZone } from '@/types/discovery'
const journey = useJourneyStore()
const router = useRouter()
const zones = ref<TreeZone[]>([])
const loading = ref(false)
const error = ref('')
const cards = computed(() =>
  journey.startLocation
    ? rankRecommendations(zones.value, journey.startLocation, journey.preferences).slice(0, 3)
    : [],
)
onMounted(() => journey.initialize())
watch(
  () => journey.originPrecinct?.id,
  async (id, _, onCleanup) => {
    const controller = new AbortController()
    onCleanup(() => controller.abort())
    zones.value = []
    error.value = ''
    if (!id) return
    loading.value = true
    try {
      const result = await getPrecinctZones(id, 500, controller.signal)
      if (!controller.signal.aborted) zones.value = result
    } catch {
      if (!controller.signal.aborted) error.value = 'Areas could not be loaded. Please try again.'
    } finally {
      if (!controller.signal.aborted) loading.value = false
    }
  },
  { immediate: true },
)
async function retry() {
  if (!journey.originPrecinct) {
    await journey.initialize()
    return
  }
  loading.value = true
  try {
    zones.value = await getPrecinctZones(journey.originPrecinct.id)
    error.value = ''
  } catch {
    error.value = 'Areas could not be loaded. Please try again.'
  } finally {
    loading.value = false
  }
}
function choose(zone: TreeZone) {
  journey.destination = { id: zone.id, label: zone.label, coordinates: zone.center }
  journey.travelMode = 'WALK'
  void router.push('/personalised-route')
}
</script>
<template>
  <AppHeader />
  <main class="page-container journey-page">
    <header class="journey-intro">
      <span class="eyebrow">Explore — Recommendations</span>
      <h1>A greener place for your next break.</h1>
      <p v-if="journey.startLocation">
        Starting from {{ journey.startLocationLabel }} ·
        {{ journey.preferences.walkingMinutes }} minutes walking
      </p>
      <RouterLink class="text-action" to="/">Edit location and preferences</RouterLink>
    </header>
    <ElAlert
      v-if="!journey.ready && !journey.loading"
      title="Choose a supported starting location and complete your preferences on the homepage."
      type="info"
      :closable="false"
    />
    <p v-else-if="loading || journey.loading" role="status">
      Finding areas that match your preferences…
    </p>
    <div v-else-if="error || journey.error" role="alert">
      <p>{{ error || journey.error }}</p>
      <ElButton @click="retry">Retry</ElButton>
    </div>
    <template v-else>
      <ElAlert
        v-if="cards.length && !cards[0]?.withinTime"
        title="No area fits the estimated walking time. Here are the closest available matches; you can increase your walking time."
        type="warning"
        :closable="false"
      />
      <div v-if="cards.length" class="recommendation-grid">
        <AreaRecommendationCard
          v-for="(area, index) in cards"
          :key="area.id"
          :area="area"
          :rank="index + 1"
          @choose="choose(area)"
        />
      </div>
      <ElEmpty
        v-else
        description="No tree areas are recorded for this precinct. Try another starting location."
      />
      <p class="muted">
        Recommendations compare recorded areas in {{ journey.originPrecinct?.name }}. Park trees are
        used as a shade and noise proxy. Actual conditions may differ.
      </p>
    </template>
  </main>
</template>
