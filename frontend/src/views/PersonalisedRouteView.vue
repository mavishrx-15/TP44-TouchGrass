<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import LocationSearch from '@/components/LocationSearch.vue'
import PersonalisedRouteCard from '@/components/PersonalisedRouteCard.vue'
import GoogleMapCanvas from '@/components/GoogleMapCanvas.vue'
import { useJourneyStore } from '@/stores/journey'
import { getWalkingRoutes } from '@/services/discovery.service'
import type { RouteOption, RoutePlace } from '@/types/discovery'
const journey = useJourneyStore()
const origin = computed<RoutePlace | null>({
  get: () =>
    journey.startLocation
      ? { id: 'origin', label: journey.startLocationLabel, coordinates: journey.startLocation }
      : null,
  set: journey.setStart,
})
const result = ref<RouteOption | null>(null)
const loading = ref(false)
const error = ref('')
const mapError = ref('')
let controller: AbortController | undefined
const canCalculate = computed(() => journey.ready && !!journey.destination)
const navigationUrl = computed(() => {
  if (!result.value || !journey.startLocation || !journey.destination) return ''
  const p = new URLSearchParams({
    api: '1',
    origin: `${journey.startLocation.lat},${journey.startLocation.lng}`,
    destination: `${journey.destination.coordinates.lat},${journey.destination.coordinates.lng}`,
    travelmode: journey.travelMode === 'WALK' ? 'walking' : 'transit',
  })
  return `https://www.google.com/maps/dir/?${p}`
})
async function calculate() {
  controller?.abort()
  result.value = null
  error.value = ''
  if (!canCalculate.value || !journey.startLocation || !journey.destination) return
  const start = journey.startLocation
  const end = journey.destination.coordinates
  if (start.lat === end.lat && start.lng === end.lng) {
    error.value = 'Choose a destination different from your starting location.'
    return
  }
  const abort = new AbortController()
  controller = abort
  loading.value = true
  try {
    const routes = await getWalkingRoutes(
      start,
      end,
      journey.preferences,
      journey.travelMode,
      abort.signal,
    )
    if (abort.signal.aborted) return
    if (!routes[0]) throw new Error('No route')
    result.value = routes[0]
  } catch {
    if (!abort.signal.aborted)
      error.value =
        'No route could be calculated. Check your destination, try another mode or retry.'
  } finally {
    if (!abort.signal.aborted) loading.value = false
  }
}
watch(
  [
    () => journey.startLocation,
    () => journey.destination,
    () => journey.travelMode,
    () => journey.preferences,
  ],
  () => {
    controller?.abort()
    loading.value = false
    result.value = null
    error.value = ''
    if (canCalculate.value) void calculate()
  },
  { deep: true },
)
onMounted(async () => {
  await journey.initialize()
  if (canCalculate.value) await calculate()
})
onBeforeUnmount(() => controller?.abort())
</script>
<template>
  <AppHeader />
  <main class="page-container journey-page">
    <header class="journey-intro">
      <span class="eyebrow">Personalised Route</span>
      <h1>Your way to a greener destination.</h1>
      <RouterLink to="/" class="text-action">Edit preferences</RouterLink>
    </header>
    <div class="personalised-layout">
      <section class="journey-panel route-form">
        <LocationSearch
          v-model="origin"
          label="Starting location"
          :precincts="journey.precincts"
          allow-geolocation
        />
        <LocationSearch
          v-model="journey.destination"
          label="Destination"
          :precincts="journey.precincts"
        />
        <ElRadioGroup v-model="journey.travelMode" aria-label="Transport mode"
          ><ElRadioButton value="WALK">Walking</ElRadioButton
          ><ElRadioButton value="TRANSIT">Transport</ElRadioButton></ElRadioGroup
        >
        <p v-if="!journey.ready" class="muted">
          Choose a supported starting location and complete your preferences on the homepage.
        </p>
        <ElButton type="primary" :disabled="!canCalculate" :loading="loading" @click="calculate">{{
          result ? 'Recalculate route' : 'Calculate route'
        }}</ElButton>
        <ElAlert v-if="error" :title="error" type="error" :closable="false" />
        <p v-if="loading" role="status">Comparing routes with your preferences…</p>
        <PersonalisedRouteCard v-if="result" :route="result" />
        <template v-if="navigationUrl"
          ><a
            class="navigation-link"
            :href="navigationUrl"
            target="_blank"
            rel="noopener noreferrer"
            >Open directions in Google Maps ↗</a
          ><small class="muted"
            >Live navigation opens in Google Maps, which may calculate a different path.
            Turn-by-turn navigation inside TouchGrass is deferred.</small
          ></template
        >
      </section>
      <section v-if="journey.startLocation" class="personalised-map" aria-label="Route map">
        <GoogleMapCanvas
          :center="journey.startLocation"
          :trees="[]"
          :zones="[]"
          :directions-open="!!result"
          :route-options="result ? [result] : []"
          @error="mapError = $event"
        /><ElAlert
          v-if="mapError"
          class="route-map-error"
          :title="mapError"
          type="info"
          :closable="false"
        />
      </section>
    </div>
  </main>
</template>
<style scoped>
.personalised-layout {
  display: grid;
  grid-template-columns: minmax(320px, 0.9fr) minmax(0, 1.1fr);
  gap: 24px;
  align-items: start;
}
.route-form {
  display: grid;
  gap: 22px;
}
.personalised-map {
  position: relative;
  height: 660px;
  overflow: hidden;
  border-radius: 20px;
  background: #e5ecdf;
}
.route-map-error {
  position: absolute;
  bottom: 20px;
  left: 20px;
  width: calc(100% - 40px);
}
.navigation-link {
  display: block;
  padding: 14px;
  text-align: center;
  background: var(--tg-green-700);
  color: white;
  border-radius: 10px;
}
@media (max-width: 900px) {
  .personalised-layout {
    grid-template-columns: 1fr;
  }
  .personalised-map {
    height: 420px;
  }
}
</style>
