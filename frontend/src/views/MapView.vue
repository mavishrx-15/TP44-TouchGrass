<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Close, Location, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import GoogleMapCanvas from '@/components/GoogleMapCanvas.vue'
import MapFiltersPanel from '@/components/MapFiltersPanel.vue'
import RoutePlanner from '@/components/RoutePlanner.vue'
import { useDiscoveryStore } from '@/stores/discovery'
import type { RouteOption, TreeRecord, TreeZone } from '@/types/discovery'

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
  distanceFilter,
} = storeToRefs(discovery)

const mapCanvas = ref<InstanceType<typeof GoogleMapCanvas> | null>(null)
const searchQuery = ref(selectedPrecinct.value.name)
const directionsOpen = ref(route.query.directions === 'true')
const mapError = ref<string | null>(null)

const visibleZones = computed(() =>
  rankedZones.value.filter(
    (zone) =>
      densityFilters.value.includes(zone.density) && zone.distanceKm <= distanceFilter.value,
  ),
)

const visibleTrees = computed(() =>
  discovery.trees.filter(
    (tree) =>
      tree.precinctId === selectedPrecinct.value.id &&
      tree.distanceKm <= distanceFilter.value &&
      (!genusFilters.value.length || genusFilters.value.includes(tree.genus)),
  ),
)

const resultCount = computed(() => visibleTrees.value.length + visibleZones.value.length)

function searchMap() {
  if (!discovery.search(searchQuery.value)) {
    ElMessage.warning(discovery.searchError ?? 'No matching precinct found')
    return
  }
  searchQuery.value = selectedPrecinct.value.name
  ElMessage.success(`Map centred on ${selectedPrecinct.value.name}`)
}

function selectTree(tree: TreeRecord) {
  selectedTree.value = tree
  selectedZone.value = null
}

function selectZone(zone: TreeZone) {
  selectedZone.value = zone
  selectedTree.value = null
}

function closeDetails() {
  selectedTree.value = null
  selectedZone.value = null
}

function selectRoute(id: RouteOption['id']) {
  selectedRouteId.value = id
}

watch(
  () => route.query.zone,
  (zoneId) => {
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
        :directions-open="directionsOpen"
        :selected-route-id="selectedRouteId"
        @select-tree="selectTree"
        @select-zone="selectZone"
        @error="mapError = $event"
      />

      <div v-if="mapError" class="map-error">
        <ElAlert :title="mapError" type="error" show-icon :closable="false" />
      </div>

      <form v-if="!directionsOpen" class="map-search" @submit.prevent="searchMap">
        <ElInput
          v-model="searchQuery"
          :prefix-icon="Search"
          placeholder="Search a Melbourne precinct"
          clearable
        />
        <ElButton native-type="submit">Search</ElButton>
        <ElButton type="primary" :icon="Location" @click="directionsOpen = true">
          Directions
        </ElButton>
      </form>

      <MapFiltersPanel
        v-model:densities="densityFilters"
        v-model:genera="genusFilters"
        v-model:distance="distanceFilter"
        @reset="discovery.resetFilters"
      />

      <RoutePlanner
        v-if="directionsOpen"
        :options="discovery.routeOptions"
        :selected-id="selectedRouteId"
        @select="selectRoute"
        @close="directionsOpen = false"
      />

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
              <dd>{{ selectedZone.dominantGenus }}</dd>
            </div>
          </dl>
          <ElButton type="primary" size="small" @click="directionsOpen = true">
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
  width: min(580px, calc(100% - 520px));
  padding: 8px;
  border-radius: 14px;
  background: rgb(255 255 255 / 97%);
  box-shadow: 0 8px 28px rgb(31 68 35 / 14%);
  transform: translateX(-50%);
}

.map-search .el-button + .el-button {
  margin-left: 6px;
}

.detail-card {
  position: absolute;
  z-index: 11;
  right: 22px;
  bottom: 58px;
  width: 290px;
  padding: 20px;
  border: 1px solid var(--tg-border);
  border-radius: 14px;
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
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.detail-card h2 {
  margin: 8px 24px 4px 0;
  color: var(--tg-green-950);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.15rem;
}

.detail-card em {
  color: var(--tg-muted);
  font-size: 0.76rem;
}

.detail-card dl {
  display: grid;
  gap: 8px;
  margin: 16px 0;
}

.detail-card dl div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.detail-card dt {
  color: var(--tg-muted);
  font-size: 0.7rem;
}

.detail-card dd {
  margin: 0;
  color: var(--tg-text);
  font-size: 0.72rem;
  font-weight: 700;
  text-align: right;
}

.reset-view {
  position: absolute;
  z-index: 8;
  right: 18px;
  bottom: 18px;
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

  .map-search .el-button:last-child {
    display: none;
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
