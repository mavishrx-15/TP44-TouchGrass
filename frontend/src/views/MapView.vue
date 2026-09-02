<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Close, Edit, Location, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import GoogleMapCanvas from '@/components/GoogleMapCanvas.vue'
import MapFiltersPanel from '@/components/MapFiltersPanel.vue'
import RoutePlanner from '@/components/RoutePlanner.vue'
import { useDiscoveryStore } from '@/stores/discovery'
import type {
  Coordinates,
  RouteEndpoint,
  RouteOption,
  TreeRecord,
  TreeZone,
} from '@/types/discovery'

const route = useRoute()
const discovery = useDiscoveryStore()
const {
  selectedPrecinct,
  rankedZones,
  selectedTree,
  selectedZone,
  selectedRouteId,
  densityFilters,
  genusFilters,
  loadError,
  isLoading,
} = storeToRefs(discovery)

onMounted(() => discovery.initialize())

const mapCanvas = ref<InstanceType<typeof GoogleMapCanvas> | null>(null)
const searchQuery = ref(selectedPrecinct.value.name)
const directionsOpen = ref(route.query.directions === 'true')
const plannerCollapsed = ref(false)
const routeDestination = ref<TreeZone | null>(null)
const mapError = ref<string | null>(null)

const visibleZones = computed(() =>
  rankedZones.value.filter((zone) => densityFilters.value.includes(zone.density)),
)

const visibleTrees = computed(() =>
  discovery.trees.filter(
    (tree) =>
      tree.precinctId === selectedPrecinct.value.id &&
      (!genusFilters.value.length || genusFilters.value.includes(tree.genus)),
  ),
)

const resultCount = computed(() => visibleTrees.value.length + visibleZones.value.length)

const selectedRouteOption = computed(() =>
  discovery.routeOptions.find((option) => option.id === selectedRouteId.value),
)

async function searchMap() {
  if (!(await discovery.search(searchQuery.value))) {
    ElMessage.warning(discovery.searchError ?? discovery.loadError ?? 'No matching precinct found')
    return
  }
  searchQuery.value = selectedPrecinct.value.name
  ElMessage.success(`Map centred on ${selectedPrecinct.value.name}`)
}

function suggestPrecincts(query: string, callback: (items: { value: string }[]) => void) {
  const normalized = query.trim().toLocaleLowerCase()
  callback(
    discovery.precincts
      .filter((precinct) => precinct.name.toLocaleLowerCase().includes(normalized))
      .map((precinct) => ({ value: precinct.name })),
  )
}

function selectTree(tree: TreeRecord) {
  selectedTree.value = tree
  selectedZone.value = null
}

function selectZone(zone: TreeZone) {
  selectedZone.value = zone
  selectedTree.value = null
}

async function openDirections(zone?: TreeZone) {
  routeDestination.value = zone ?? null
  directionsOpen.value = true
  plannerCollapsed.value = false
  if (zone) {
    selectedZone.value = zone
    selectedTree.value = null
    mapCanvas.value?.focusZone(zone)
    await planRouteEndpoints(null, zone)
  }
}

async function planRouteEndpoints(
  originEndpoint: RouteEndpoint,
  destinationEndpoint: RouteEndpoint,
) {
  const location = currentLocation()
  const origin = endpointCoordinates(originEndpoint, location)
  const destination = endpointCoordinates(destinationEndpoint, location)
  if (origin.lat === destination.lat && origin.lng === destination.lng) {
    ElMessage.warning('Origin and destination must be different.')
    return
  }
  if (destinationEndpoint && 'center' in destinationEndpoint) {
    selectedZone.value = destinationEndpoint
    mapCanvas.value?.focusZone(destinationEndpoint)
  }
  if (!(await discovery.planRoutes(origin, destination))) {
    ElMessage.error(discovery.routeError ?? 'Routes could not be loaded')
  }
}

function endpointCoordinates(endpoint: RouteEndpoint, location: Coordinates): Coordinates {
  if (!endpoint) return location
  return 'center' in endpoint ? endpoint.center : endpoint.coordinates
}

// "My location" is fixed to Melbourne central rather than the device's real
// position, so route planning stays deterministic across devices/browsers.
const MELBOURNE_CENTRAL: Coordinates = { lat: -37.8136, lng: 144.9631 }

function currentLocation(): Coordinates {
  return MELBOURNE_CENTRAL
}

function closeDetails() {
  selectedTree.value = null
  selectedZone.value = null
}

function selectRoute(id: RouteOption['id']) {
  selectedRouteId.value = id
  // Selecting a route means the person wants to look at the map, not the
  // planner card, so tuck the card away while keeping the route rendered.
  plannerCollapsed.value = true
}

function closeDirections() {
  directionsOpen.value = false
  plannerCollapsed.value = false
}

watch(
  [() => route.query.zone, rankedZones],
  ([zoneId]) => {
    if (typeof zoneId !== 'string') return
    const zone = rankedZones.value.find((candidate) => candidate.id === zoneId)
    if (zone) selectZone(zone)
  },
  { immediate: true },
)
</script>

<template>
  <AppHeader />
  <main class="map-page">
    <div class="map-canvas">
      <GoogleMapCanvas
        ref="mapCanvas"
        :center="selectedPrecinct.referencePoint"
        :trees="visibleTrees"
        :zones="visibleZones"
        :directions-open="directionsOpen && discovery.routeOptions.length > 0"
        :selected-route-id="selectedRouteId"
        :route-options="discovery.routeOptions"
        @select-tree="selectTree"
        @select-zone="selectZone"
        @error="mapError = $event"
      />

      <div v-if="mapError" class="map-error">
        <ElAlert :title="mapError" type="error" show-icon :closable="false" />
      </div>

      <div v-if="loadError" class="map-error">
        <ElAlert :title="loadError" type="error" show-icon :closable="false" />
      </div>

      <form v-if="!directionsOpen" class="map-search" @submit.prevent="searchMap">
        <ElAutocomplete
          v-model="searchQuery"
          :fetch-suggestions="suggestPrecincts"
          :prefix-icon="Search"
          placeholder="Search tree-data areas"
          clearable
          :loading="isLoading"
          select-when-unmatched
          @select="searchMap"
        />
        <ElButton
          class="search-submit"
          type="primary"
          :icon="Location"
          @click="openDirections()"
        >
          Directions
        </ElButton>
      </form>

      <MapFiltersPanel
        v-model:densities="densityFilters"
        v-model:genera="genusFilters"
        :genus-options="discovery.availableGenera"
        @reset="discovery.resetFilters"
      />

      <RoutePlanner
        v-if="directionsOpen && !plannerCollapsed"
        :options="discovery.routeOptions"
        :selected-id="selectedRouteId"
        :zones="rankedZones"
        :initial-destination="routeDestination"
        :loading="discovery.routesLoading"
        :error="discovery.routeError"
        @select="selectRoute"
        @route="planRouteEndpoints"
        @close="closeDirections"
      />

      <div v-else-if="directionsOpen && plannerCollapsed" class="route-summary">
        <div class="route-summary-info">
          <span class="route-summary-icon" aria-hidden="true">
            {{ selectedRouteOption?.id === 'green' ? '♧' : 'ϟ' }}
          </span>
          <span>
            <strong>{{ selectedRouteOption?.label ?? 'Route selected' }}</strong>
            <small v-if="selectedRouteOption">
              {{ selectedRouteOption.durationMinutes }} min ·
              {{ selectedRouteOption.distanceKm.toFixed(1) }} km ·
              {{ selectedRouteOption.treeCount }} trees
            </small>
          </span>
        </div>
        <div class="route-summary-actions">
          <ElButton text :icon="Edit" @click="plannerCollapsed = false">Edit</ElButton>
          <ElButton
            text
            circle
            :icon="Close"
            aria-label="Close directions"
            @click="closeDirections"
          />
        </div>
      </div>

      <section v-if="selectedTree || selectedZone" class="detail-card">
        <ElButton
          class="detail-close"
          text
          circle
          :icon="Close"
          aria-label="Close details"
          @click="closeDetails"
        />
        <template v-if="selectedTree">
          <span class="detail-eyebrow">Individual tree</span>
          <h2>{{ selectedTree.commonName }}</h2>
          <em>{{ selectedTree.scientificName }}</em>
          <dl>
            <div>
              <dt>Genus</dt>
              <dd>{{ selectedTree.genus }}</dd>
            </div>
            <div>
              <dt>Planting age</dt>
              <dd>{{ selectedTree.plantingAge }}</dd>
            </div>
          </dl>
        </template>
        <template v-else-if="selectedZone">
          <span class="detail-eyebrow">Tree-density zone</span>
          <h2>{{ selectedZone.label }}</h2>
          <dl>
            <div>
              <dt>Tree count</dt>
              <dd>{{ selectedZone.treeCount }}</dd>
            </div>
            <div>
              <dt>Density tier</dt>
              <dd>{{ selectedZone.density }}</dd>
            </div>
            <div>
              <dt>Dominant genus</dt>
              <dd>{{ selectedZone.dominantGenus ?? 'Mixed / other' }}</dd>
            </div>
          </dl>
          <ElButton type="primary" size="small" @click="openDirections(selectedZone)">
            Plan a route here
          </ElButton>
        </template>
      </section>

      <ElButton class="reset-view" :icon="Refresh" @click="mapCanvas?.resetView()">
        Reset view
      </ElButton>

      <div class="map-status" role="status">
        {{ selectedPrecinct.name }} · {{ resultCount }} visible features
      </div>
    </div>
  </main>
</template>

<style scoped>
.map-page {
  height: calc(100vh - 68px);
  min-height: 620px;
  overflow: hidden;
}

.map-canvas {
  position: relative;
  height: 100%;
  overflow: hidden;
  background: #eef2e8;
}

.map-error {
  position: absolute;
  z-index: 20;
  top: 90px;
  left: 50%;
  width: min(560px, calc(100% - 40px));
  transform: translateX(-50%);
}

.map-search {
  position: absolute;
  z-index: 10;
  top: 22px;
  left: 50%;
  display: flex;
  align-items: center;
  gap: 16px;
  width: min(460px, calc(100% - 520px));
  padding: 8px;
  border-radius: 14px;
  background: rgb(255 255 255 / 97%);
  box-shadow: 0 8px 28px rgb(31 68 35 / 14%);
  transform: translateX(-50%);
}

.map-search :deep(.el-autocomplete) {
  flex: 1 1 auto;
  min-width: 0;
}

.map-search .search-submit {
  flex-shrink: 0;
}

.route-summary {
  position: absolute;
  z-index: 12;
  top: 22px;
  left: 50%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: min(520px, calc(100% - 500px));
  padding: 10px 10px 10px 16px;
  border: 1px solid rgb(23 53 29 / 12%);
  border-radius: 14px;
  background: rgb(255 255 255 / 98%);
  box-shadow: 0 14px 38px rgb(31 68 35 / 20%);
  transform: translateX(-50%);
}

.route-summary-info {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.route-summary-icon {
  color: var(--tg-green-700);
  font-size: 1.15rem;
}

.route-summary-info strong,
.route-summary-info small {
  display: block;
}

.route-summary-info strong {
  color: var(--tg-green-800);
  font-size: 0.85rem;
}

.route-summary-info small {
  margin-top: 2px;
  color: var(--tg-muted);
  font-size: 0.68rem;
  white-space: nowrap;
}

.route-summary-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 2px;
}

.detail-card {
  position: absolute;
  z-index: 11;
  right: 22px;
  bottom: 58px;
  width: min(390px, calc(100% - 44px));
  padding: 28px;
  border: 1px solid var(--tg-border);
  border-radius: 20px;
  background: white;
  box-shadow: 0 10px 30px rgb(31 68 35 / 18%);
}

.detail-close {
  position: absolute;
  top: 8px;
  right: 8px;
}

.detail-eyebrow {
  color: var(--tg-green-700);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.detail-card h2 {
  margin: 8px 24px 4px 0;
  color: var(--tg-green-950);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.65rem;
}

.detail-card em {
  color: var(--tg-muted);
  font-size: 0.76rem;
}

.detail-card dl {
  display: grid;
  gap: 12px;
  margin: 20px 0;
}

.detail-card dl div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.detail-card dt {
  color: var(--tg-muted);
  font-size: 0.8rem;
}

.detail-card dd {
  margin: 0;
  color: var(--tg-text);
  font-size: 0.82rem;
  font-weight: 700;
  text-align: right;
}

.reset-view {
  position: absolute;
  z-index: 8;
  right: 18px;
  bottom: 108px;
  border-color: var(--tg-border);
  box-shadow: 0 4px 14px rgb(31 68 35 / 14%);
}

.map-status {
  position: absolute;
  z-index: 7;
  bottom: 22px;
  left: 50%;
  padding: 7px 11px;
  border-radius: 8px;
  background: rgb(255 255 255 / 90%);
  color: var(--tg-muted);
  font-size: 0.68rem;
  box-shadow: 0 4px 14px rgb(31 68 35 / 12%);
  transform: translateX(-50%);
}

@media (max-width: 900px) {
  .map-search {
    right: 12px;
    left: auto;
    width: min(480px, calc(100% - 260px));
    transform: none;
  }

  .route-summary {
    right: 12px;
    left: auto;
    width: min(470px, calc(100% - 214px));
    transform: none;
  }
}

@media (max-width: 720px) {
  .map-page {
    height: calc(100vh - 68px);
    min-height: 580px;
  }

  .map-search {
    top: 10px;
    left: 12px;
    width: calc(100% - 24px);
  }

  .route-summary {
    top: 10px;
    right: 12px;
    width: calc(100% - 24px);
  }

  .detail-card {
    right: 12px;
    bottom: 56px;
    width: calc(100% - 24px);
  }

  .map-status {
    display: none;
  }
}
</style>
