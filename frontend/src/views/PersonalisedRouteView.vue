<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Guide, Location, Position, Refresh, Van } from '@element-plus/icons-vue'
import JourneyHeader from '@/components/JourneyHeader.vue'
import DemoNotice from '@/components/DemoNotice.vue'
import GoogleMapCanvas from '@/components/GoogleMapCanvas.vue'
import LocationSearch from '@/components/LocationSearch.vue'
import MapFiltersPanel from '@/components/MapFiltersPanel.vue'
import { useJourneyStore } from '@/stores/journey'
import { useAccessibilityStore } from '@/stores/accessibility'
import { USE_MOCK_DATA } from '@/services/personalisation.service'
import { getSpecies } from '@/services/discovery.service'
import { canopyLabel, noiseLabel } from '@/services/preferences'
import type { DensityTier, RoutePlace, TreeGenus } from '@/types/discovery'

const journey = useJourneyStore()
const accessibility = useAccessibilityStore()
const locationError = ref('')
const mapError = ref('')
const locating = ref(false)
const initialising = ref(false)
const densityFilters = ref<DensityTier[]>(['High', 'Medium', 'Low'])
const genusFilters = ref<TreeGenus[]>([])
const genusOptions = ref<TreeGenus[]>([])
const visibleZones = computed(() =>
  journey.areas.filter((area) => densityFilters.value.includes(area.density)),
)
// Matches the legacy map's own tree cap: each marker is a real DOM element
// (AdvancedMarkerElement), and areas here carry up to 5000 trees each for
// per-zone stats accuracy - rendering all of them at once is what froze the
// page. 500 mirrors what /api/trees?...&limit=500 already caps MapView to.
const VISIBLE_TREE_LIMIT = 500
const visibleTrees = computed(() =>
  journey.areas
    .flatMap((area) =>
      (area.trees ?? []).filter(
        (tree) => !genusFilters.value.length || genusFilters.value.includes(tree.genus),
      ),
    )
    .slice(0, VISIBLE_TREE_LIMIT),
)
function resetMapFilters() {
  densityFilters.value = ['High', 'Medium', 'Low']
  genusFilters.value = []
}
const center = computed(
  () =>
    journey.destination?.coordinates ??
    journey.startLocation?.coordinates ?? { lat: -37.7934, lng: 144.9305 },
)
const navigationUrl = computed(() => {
  if (!journey.startLocation || !journey.destination) return '#'
  const origin = journey.startLocation.coordinates,
    destination = journey.destination.coordinates
  const query = new URLSearchParams({
    api: '1',
    origin: `${origin.lat},${origin.lng}`,
    destination: `${destination.lat},${destination.lng}`,
    travelmode: journey.travelMode === 'WALK' ? 'walking' : 'transit',
  })
  return `https://www.google.com/maps/dir/?${query}`
})
const explanationRows = computed(() => {
  const route = journey.route
  if (!route?.metrics || !route.match || route.travelMode !== 'WALK') return []
  const matches = route.match.matches
  return matches.map((match) => ({
    key: match.key,
    title: {
      canopy: 'Tree canopy',
      shade: 'Shade & thermal comfort',
      noise: 'Noise level',
      allergy: 'Allergy preference',
      time: 'Walking time',
    }[match.key],
    subtitle: {
      canopy: 'Tree density along the path',
      shade: 'Park-side tree share',
      noise: 'Park vs. street trees nearby',
      allergy: 'High-pollen trees within 100 m',
      time:
        journey.preferences.walkingTime === 20
          ? 'Your open-ended walk'
          : `Your ${journey.preferences.walkingTime} min budget`,
    }[match.key],
    value:
      match.key === 'canopy'
        ? canopyLabel(route.metrics!.canopy)
        : match.key === 'noise'
          ? noiseLabel(route.metrics!.parkShare)
          : match.detail,
    matched: match.matched,
  }))
})

async function locate() {
  locationError.value = ''
  locating.value = true
  try {
    await journey.useCurrentLocation()
    await updateRoute()
  } catch (e) {
    locationError.value = e instanceof Error ? e.message : 'Location is unavailable.'
  } finally {
    locating.value = false
  }
}
async function updateRoute() {
  if (!journey.startLocation || !journey.destination) return
  // Areas only feed the map thumbnail/tree markers, not route scoring - run
  // them alongside the route request instead of blocking on it first.
  await Promise.all([journey.refreshAreas(), journey.calculate()])
}
async function setOrigin(value: RoutePlace | null) {
  journey.startLocation = value
  locationError.value = ''
  if (value) await updateRoute()
}
async function setDestination(value: RoutePlace | null) {
  journey.destination = value
  if (value) await updateRoute()
}
onMounted(async () => {
  initialising.value = true
  getSpecies()
    .then((species) => {
      genusOptions.value = species.map((item) => item.genus)
    })
    .catch(() => {
      /* Genus filter list is a nice-to-have; the map still works without it. */
    })
  try {
    await journey.initialize()
    if (!journey.startLocation && navigator.permissions) {
      const permission = await navigator.permissions.query({ name: 'geolocation' })
      if (permission.state === 'granted') await journey.useCurrentLocation()
    }
    await Promise.all([
      journey.startLocation && !journey.areas.length ? journey.refreshAreas() : null,
      journey.startLocation && journey.destination && !journey.route
        ? journey.calculate()
        : null,
    ])
  } catch {
    locationError.value =
      'We couldn’t load location data. Search for a starting point or try again.'
  } finally {
    initialising.value = false
  }
})
watch(
  () => journey.route,
  (route) => {
    if (!route) return
    const mode = journey.travelMode === 'WALK' ? 'Walking route' : 'Transport route'
    const sentence = route.match?.sentence ?? ''
    accessibility.speak(
      `${mode} found. ${route.distanceKm.toFixed(1)} kilometres, ${route.durationMinutes} minutes. ${sentence}`,
    )
  },
)
watch(
  () => journey.error,
  (message) => {
    if (message) accessibility.speak(message)
  },
)
</script>

<template>
  <JourneyHeader />
  <DemoNotice />
  <main id="main-content" tabindex="-1" class="personalised-page">
    <section class="journey-map" aria-label="Your route map">
      <GoogleMapCanvas
        :center="center"
        :trees="visibleTrees"
        :zones="visibleZones"
        :directions-open="!!journey.route"
        :route-options="journey.route ? [journey.route] : []"
        :origin="journey.startLocation?.coordinates"
        :destination="journey.destination?.coordinates"
        :preview-path="journey.route?.path"
        :demo="USE_MOCK_DATA"
        :auto-center="false"
        @error="mapError = $event"
      />
      <MapFiltersPanel
        v-model:densities="densityFilters"
        v-model:genera="genusFilters"
        :genus-options="genusOptions"
        @reset="resetMapFilters"
      />
      <span class="personalised-badge">✓ Personalised</span>
      <div class="journey-input-panel">
        <LocationSearch
          :model-value="journey.startLocation"
          :precincts="journey.precincts"
          label="Starting location"
          placeholder="My location"
          @update:model-value="setOrigin"
        />
        <LocationSearch
          :model-value="journey.destination"
          :precincts="journey.precincts"
          label="Destination"
          placeholder="Where would you like to go?"
          @update:model-value="setDestination"
        />
        <p v-if="journey.startLocation">
          Carried over from Home — edit here anytime, or go back to update it there.
        </p>
        <button v-else class="text-button use-location" :disabled="locating" @click="locate">
          <ElIcon><Location /></ElIcon
          >{{ locating ? 'Finding your location…' : 'Use my current location' }}
        </button>
        <p v-if="locationError" class="form-error" role="alert">{{ locationError }}</p>
      </div>
      <div v-if="mapError" class="map-unavailable notice" role="status">{{ mapError }}</div>
    </section>

    <aside
      class="route-panel"
      aria-label="Personalised route details"
      :aria-busy="journey.loading || initialising"
    >
      <div class="route-panel-top">
        <span class="route-eyebrow">{{
          journey.travelMode === 'WALK' ? 'Personalised walking route' : 'Public transport route'
        }}</span>
        <h1>{{ journey.destination?.label ?? 'A greener journey starts here.' }}</h1>
        <p class="route-subtitle" v-if="journey.selectedArea && journey.travelMode === 'WALK'">
          {{ journey.selectedArea.treeCount }} trees · {{ journey.selectedArea.density }} tree
          density at your destination
        </p>
        <p class="route-subtitle" v-else-if="!journey.destination">
          Choose your starting point and a destination, or set your preferences on Home.
        </p>

        <div class="travel-toggle" role="group" aria-label="Travel mode">
          <button
            type="button"
            :class="{ active: journey.travelMode === 'WALK' }"
            :aria-pressed="journey.travelMode === 'WALK'"
            @click="journey.calculate('WALK')"
          >
            <ElIcon><Guide /></ElIcon> Walking
          </button>
          <button
            type="button"
            :class="{ active: journey.travelMode === 'TRANSIT' }"
            :aria-pressed="journey.travelMode === 'TRANSIT'"
            @click="journey.calculate('TRANSIT')"
          >
            <ElIcon><Van /></ElIcon> Transport
          </button>
        </div>

        <div v-if="journey.loading || initialising" class="route-loading" role="status">
          <span class="route-spinner" /><strong>{{
            journey.travelMode === 'WALK'
              ? 'Finding your greener route…'
              : 'Finding a transport route…'
          }}</strong>
          <p>Your route and travel details will appear here.</p>
        </div>
        <div v-else-if="journey.error" class="route-error" role="alert">
          <p>{{ journey.error }}</p>
          <button
            class="secondary-button"
            :disabled="!journey.startLocation || !journey.destination"
            @click="journey.calculate()"
          >
            <ElIcon><Refresh /></ElIcon>Try again
          </button>
        </div>
        <template v-else-if="journey.route">
          <dl class="route-stats">
            <div>
              <dt>Distance</dt>
              <dd>{{ journey.route.distanceKm.toFixed(1) }} <span>km</span></dd>
            </div>
            <div>
              <dt>{{ journey.travelMode === 'WALK' ? 'Walk time' : 'Travel time' }}</dt>
              <dd>{{ journey.route.durationMinutes }} <span>min</span></dd>
            </div>
          </dl>
          <div v-if="journey.route.match?.matches.length" class="preference-chips route-matches">
            <span
              v-for="match in journey.route.match.matches"
              :key="match.key"
              class="preference-chip"
              :class="{ partial: !match.matched }"
              >{{ match.matched ? '✓' : '◷' }} {{ match.label
              }}{{ match.matched ? '' : ' — partial' }}</span
            >
          </div>
          <p v-if="journey.route.match" class="best-match-line">
            {{ journey.route.match.sentence }}
          </p>
          <p v-if="journey.route.message" class="notice">{{ journey.route.message }}</p>
          <section class="why-route">
            <h2>Why this route?</h2>
            <template v-if="journey.travelMode === 'WALK'">
              <dl v-if="explanationRows.length">
                <div v-for="row in explanationRows" :key="row.key">
                  <dt>
                    {{ row.title }}<small>{{ row.subtitle }}</small>
                  </dt>
                  <dd :class="{ partial: !row.matched }">
                    {{ row.value }}
                    <span class="sr-only">{{
                      row.matched ? 'Matched' : 'Does not fully match'
                    }}</span>
                  </dd>
                </div>
              </dl>
              <p v-else>
                No environmental preferences selected. This route takes you to your chosen
                destination.
              </p>
              <p v-if="journey.route.isMock">
                This preview selects one of {{ journey.route.candidateCount }} sample routes. Live
                walking alternatives will be provided by Google when connected.
              </p>
              <p v-else-if="journey.route.candidateCount > 1">
                Chosen as the best match among {{ journey.route.candidateCount }} walking routes
                Google found between these points — not a custom path built around this area.
              </p>
              <p v-else>
                Google returned one walking route between these points. Its preference matches are
                shown above.
              </p>
              <p
                v-if="journey.preferences.allergy && journey.route.metrics?.lowAllergyShare == null"
                class="allergy-explanation"
              >
                Your allergy preference is saved, but allergy route scoring is not yet available.
                This route has not been assessed for pollen exposure.
              </p>
              <p v-else-if="journey.preferences.allergy" class="allergy-explanation">
                Your allergy preference favours the least-allergenic available alternative; it does
                not create a custom detour. Allergy classifications are not yet confirmed.
              </p>
            </template>
            <p v-else>
              Public transport directions to your destination. Tree canopy, shade, noise and allergy
              preferences are not used to score transport routes.
            </p>
          </section>
        </template>
        <div v-else class="route-empty">
          <ElIcon><Location /></ElIcon>
          <h2>Where will a little green take you?</h2>
          <p>Resolve both locations above to generate your personalised route.</p>
        </div>
      </div>

      <div class="route-actions">
        <a
          v-if="
            journey.travelMode === 'TRANSIT' &&
            journey.error &&
            journey.startLocation &&
            journey.destination
          "
          class="primary-button"
          :href="navigationUrl"
          target="_blank"
          rel="noopener noreferrer"
          >Open transport directions in Google Maps ↗</a
        >
        <a
          v-if="journey.route && !journey.loading"
          class="primary-button"
          :href="navigationUrl"
          target="_blank"
          rel="noopener noreferrer"
          ><ElIcon><Position /></ElIcon>Start Navigation ↗</a
        >
        <p v-if="journey.route && !journey.loading" class="navigation-note">
          Opens Google Maps. Its directions may differ from this route.
        </p>
        <RouterLink class="secondary-button" to="/">Update Preferences</RouterLink>
        <RouterLink v-if="journey.startLocation" class="other-options" to="/explore/recommendations"
          >See other options →</RouterLink
        >
      </div>
    </aside>
  </main>
</template>

<style scoped>
.personalised-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  min-height: calc(100svh - 100px);
}
.journey-map {
  position: relative;
  min-height: 650px;
  background: #eef1e7;
}
.personalised-badge {
  position: absolute;
  bottom: 24px;
  right: 20px;
  background: white;
  border: 1px solid var(--tg-border);
  border-radius: 8px;
  padding: 9px 12px;
  color: var(--tg-green-700);
  font-weight: 700;
  font-size: 0.75rem;
  box-shadow: var(--tg-shadow);
}
.journey-input-panel {
  position: absolute;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  width: min(420px, calc(100% - 210px));
  display: grid;
  gap: 9px;
  background: white;
  border: 1px solid #e3e7de;
  border-radius: 17px;
  padding: 14px;
  box-shadow: 0 10px 30px #24412212;
}
.journey-input-panel :deep(.location-search:nth-child(2) .el-input__wrapper) {
  background: var(--tg-green-50);
  box-shadow: 0 0 0 1px #a1c87c inset;
}
.journey-input-panel p {
  margin: 0;
  font-size: 0.68rem;
  color: var(--tg-muted);
  line-height: 1.5;
}
.journey-input-panel p.form-error {
  color: #a63829;
}
.use-location {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.77rem;
  padding: 2px 0;
}
.map-unavailable {
  position: absolute;
  top: 230px;
  margin: 0 20px;
  left: 0;
  right: 0;
}
.route-panel {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: white;
  border-left: 1px solid var(--tg-border);
  padding: 24px 22px 22px;
  gap: 40px;
}
.route-eyebrow {
  display: inline-block;
  background: var(--tg-green-100);
  color: var(--tg-green-800);
  border-radius: 16px;
  padding: 5px 11px;
  font-size: 0.65rem;
  text-transform: uppercase;
  font-weight: 800;
}
h1 {
  color: var(--tg-green-950);
  font:
    bold 1.65rem/1.16 Georgia,
    serif;
  margin: 16px 0 7px;
  overflow-wrap: anywhere;
}
.route-subtitle {
  color: var(--tg-muted);
  font-size: 0.77rem;
  line-height: 1.55;
  margin: 0 0 19px;
}
.travel-toggle {
  display: flex;
  gap: 3px;
  padding: 4px;
  border-radius: 11px;
  background: var(--tg-cream);
  margin: 20px 0 17px;
}
.travel-toggle button {
  width: 50%;
  min-height: 40px;
  border: 0;
  background: none;
  border-radius: 8px;
  color: var(--tg-muted);
  font-weight: 700;
  font-size: 0.8rem;
  cursor: pointer;
}
.travel-toggle button .el-icon {
  margin-right: 7px;
  vertical-align: -2px;
}
.travel-toggle button.active {
  background: white;
  box-shadow: 0 1px 4px #24412212;
  color: var(--tg-green-800);
}
.route-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 0 0 15px;
}
.route-stats > div {
  border: 1px solid var(--tg-border);
  border-radius: 11px;
  padding: 14px;
}
.route-stats dt {
  color: var(--tg-muted);
  font-size: 0.66rem;
  text-transform: uppercase;
  font-weight: 800;
}
.route-stats dd {
  margin: 3px 0 0;
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--tg-green-950);
}
.route-stats dd span {
  font-size: 1.1rem;
}
.route-matches {
  gap: 5px;
}
.route-matches .preference-chip {
  padding: 4px 7px;
  font-size: 0.66rem;
}
.best-match-line {
  font-size: 0.76rem;
  line-height: 1.6;
  color: var(--tg-text);
}
.why-route {
  background: #f8f8f2;
  border: 1px solid var(--tg-border);
  border-radius: 12px;
  padding: 15px;
  margin-top: 18px;
}
.why-route h2 {
  margin: 0 0 6px;
  font-size: 0.87rem;
}
.why-route dl {
  margin: 0;
}
.why-route dl > div {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px solid var(--tg-border);
  font-size: 0.74rem;
}
.why-route dl > div:last-child {
  border: 0;
}
.why-route dt {
  font-weight: 650;
}
.why-route small {
  display: block;
  color: var(--tg-muted);
  font-weight: 400;
  margin-top: 3px;
}
.why-route dd {
  margin: 0;
  max-width: 46%;
  text-align: right;
  font-weight: 700;
  color: var(--tg-green-700);
  font-size: 0.72rem;
}
.why-route dd.partial {
  color: #946a1c;
}
.why-route p {
  font-size: 0.71rem;
  line-height: 1.55;
  color: var(--tg-muted);
  margin: 10px 0 0;
}
.why-route .allergy-explanation {
  color: #786129;
}
.route-actions {
  display: grid;
  gap: 9px;
}
.other-options {
  text-decoration: underline;
  text-underline-offset: 3px;
  color: var(--tg-green-800);
  text-align: center;
  padding: 9px;
  font-size: 0.8rem;
  font-weight: 700;
}
.navigation-note {
  font-size: 0.65rem;
  color: var(--tg-muted);
  text-align: center;
  margin: -3px 0 4px;
  line-height: 1.4;
}
.route-loading,
.route-empty {
  text-align: center;
  padding: 35px 15px;
  color: var(--tg-muted);
  font-size: 0.8rem;
  line-height: 1.6;
}
.route-loading strong {
  display: block;
  color: var(--tg-green-950);
}
.route-empty .el-icon {
  font-size: 2rem;
  color: var(--tg-green-700);
}
.route-empty h2 {
  font:
    bold 1.4rem Georgia,
    serif;
  color: var(--tg-green-950);
}
.route-spinner {
  display: inline-block;
  border-radius: 50%;
  border: 3px solid var(--tg-border);
  border-top-color: var(--tg-green-700);
  width: 30px;
  height: 30px;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}
.route-error {
  padding: 18px;
  background: #fff4ed;
  color: #92472d;
  border-radius: 10px;
  font-size: 0.85rem;
  line-height: 1.6;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (min-width: 1400px) {
  .personalised-page {
    grid-template-columns: minmax(0, 1fr) 430px;
  }
  .route-panel {
    padding: 30px;
  }
}
@media (max-width: 1100px) {
  .journey-input-panel {
    left: 18px;
    width: calc(100% - 36px);
    transform: none;
    top: 67px;
  }
  .personalised-badge {
    right: 18px;
    bottom: 16px;
    padding: 7px 10px;
  }
}
@media (max-width: 760px) {
  .personalised-page {
    grid-template-columns: 1fr;
  }
  .journey-map {
    min-height: 540px;
  }
  .journey-input-panel {
    top: 57px;
    padding: 11px;
    gap: 8px;
  }
  .journey-input-panel :deep(.el-input__wrapper) {
    min-height: 43px;
  }
  .route-panel {
    border-left: 0;
    border-top: 1px solid var(--tg-border);
    padding: 23px 18px;
    gap: 26px;
  }
  h1 {
    font-size: 1.55rem;
  }
  .travel-toggle button {
    min-height: 44px;
  }
  .route-matches .preference-chip {
    font-size: 0.72rem;
  }
  .why-route dl > div {
    font-size: 0.8rem;
  }
  .why-route dd {
    font-size: 0.77rem;
  }
  .why-route p {
    font-size: 0.77rem;
  }
  .route-actions {
    padding-bottom: env(safe-area-inset-bottom);
  }
}
</style>
