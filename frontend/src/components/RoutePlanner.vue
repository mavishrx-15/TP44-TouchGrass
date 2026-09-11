<script setup lang="ts">
import { ArrowDown, ArrowLeft, ArrowUp, Location, Search, Sort } from '@element-plus/icons-vue'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { getPlaceDetails, getPlaceSuggestions } from '@/services/discovery.service'
import type {
  PlaceSuggestion,
  RouteEndpoint,
  RouteOption,
  RoutePlace,
  TreeZone,
} from '@/types/discovery'

const props = withDefaults(
  defineProps<{
    options?: RouteOption[]
    zones?: TreeZone[]
    initialDestination?: TreeZone | null
    loading?: boolean
    error?: string | null
    collapsed?: boolean
  }>(),
  {
    options: () => [],
    zones: () => [],
    collapsed: false,
  },
)
const emit = defineEmits<{
  select: [id: RouteOption['id']]
  route: [origin: RouteEndpoint, destination: RouteEndpoint]
  close: []
  'toggle-collapse': []
}>()

const origin = ref('My location')
const destination = ref('')
const selectedOrigin = ref<RouteEndpoint>(null)
const selectedDestination = ref<RouteEndpoint>(null)
const activeInput = ref<'origin' | 'destination' | null>('destination')
const placeSuggestions = ref<PlaceSuggestion[]>([])
const placesLoading = ref(false)
const placesError = ref<string | null>(null)
let suggestionTimer: ReturnType<typeof setTimeout> | undefined

const activeQuery = computed(() =>
  (activeInput.value === 'origin' ? origin.value : destination.value).trim(),
)
const filteredZones = computed(() => {
  const query = activeQuery.value.toLocaleLowerCase()
  if (query.length < 2) return props.zones.slice(0, 12)
  return props.zones.filter((zone) => zone.label.toLocaleLowerCase().includes(query)).slice(0, 12)
})

// Wait for typing to pause before querying Google Places.
watch([activeInput, origin, destination], () => {
  clearTimeout(suggestionTimer)
  placeSuggestions.value = []
  placesError.value = null
  if (!activeInput.value) return
  const query = activeQuery.value
  if (query.length < 2 || query.toLocaleLowerCase() === 'my location') return
  suggestionTimer = setTimeout(async () => {
    placesLoading.value = true
    try {
      placeSuggestions.value = await getPlaceSuggestions(query)
    } catch {
      placesError.value = 'Google place suggestions are unavailable.'
    } finally {
      placesLoading.value = false
    }
  }, 250)
})

onBeforeUnmount(() => clearTimeout(suggestionTimer))

watch(
  () => props.initialDestination,
  (zone) => {
    if (!zone) return
    selectedDestination.value = zone
    selectedOrigin.value = null
    origin.value = 'My location'
    destination.value = zone.label
    activeInput.value = null
  },
  { immediate: true },
)

function edit(field: 'origin' | 'destination', value: string) {
  activeInput.value = field
  if (field === 'origin') {
    origin.value = value
    selectedOrigin.value = null
  } else {
    destination.value = value
    selectedDestination.value = null
  }
}

function chooseZone(zone: TreeZone) {
  if (activeInput.value === 'origin') {
    origin.value = zone.label
    selectedOrigin.value = zone
  } else {
    destination.value = zone.label
    selectedDestination.value = zone
  }
  activeInput.value = null
  requestRoute()
}

async function choosePlace(suggestion: PlaceSuggestion) {
  placesLoading.value = true
  try {
    const place = await getPlaceDetails(suggestion.id)
    setEndpoint(place)
    requestRoute()
  } catch {
    placesError.value = 'This Google place could not be loaded.'
  } finally {
    placesLoading.value = false
  }
}

function setEndpoint(place: RoutePlace) {
  if (activeInput.value === 'origin') {
    origin.value = place.label
    selectedOrigin.value = place
  } else {
    destination.value = place.label
    selectedDestination.value = place
  }
  activeInput.value = null
}

function chooseMyLocation() {
  if (activeInput.value === 'origin') {
    origin.value = 'My location'
    selectedOrigin.value = null
  } else {
    destination.value = 'My location'
    selectedDestination.value = null
  }
  activeInput.value = null
  requestRoute()
}

function swapDirection() {
  ;[origin.value, destination.value] = [destination.value, origin.value]
  ;[selectedOrigin.value, selectedDestination.value] = [
    selectedDestination.value,
    selectedOrigin.value,
  ]
  activeInput.value = null
  requestRoute()
}

function requestRoute() {
  if (!origin.value.trim() || !destination.value.trim()) return
  emit('route', selectedOrigin.value, selectedDestination.value)
}
</script>

<template>
  <section class="route-planner" :class="{ collapsed }" aria-label="Route planner">
    <button v-if="collapsed" type="button" class="collapsed-bar" @click="emit('toggle-collapse')">
      <ElIcon><Location /></ElIcon>
      <span>{{ destination || 'Directions' }}</span>
      <ElIcon><ArrowDown /></ElIcon>
      <ElButton
        text
        circle
        :icon="ArrowLeft"
        aria-label="Close directions"
        @click.stop="emit('close')"
      />
    </button>

    <template v-else>
      <header class="planner-header">
        <ElButton
          text
          circle
          :icon="ArrowLeft"
          aria-label="Close directions"
          @click="emit('close')"
        />
        <div class="route-inputs">
          <ElInput
            :model-value="origin"
            :prefix-icon="Location"
            placeholder="Choose an origin"
            clearable
            @focus="activeInput = 'origin'"
            @update:model-value="edit('origin', String($event))"
          />
          <span class="input-connector" aria-hidden="true" />
          <ElInput
            :model-value="destination"
            :prefix-icon="Search"
            placeholder="Search an area or place"
            clearable
            @focus="activeInput = 'destination'"
            @update:model-value="edit('destination', String($event))"
          />
        </div>
        <ElButton
          class="swap-button"
          :icon="Sort"
          aria-label="Swap origin and destination"
          :disabled="!origin.trim() || !destination.trim()"
          @click="swapDirection"
        />
        <ElButton
          v-if="!activeInput"
          class="collapse-toggle"
          text
          circle
          :icon="ArrowUp"
          aria-label="Hide panel to view the full route"
          @click="emit('toggle-collapse')"
        />
      </header>

      <div v-if="activeInput" v-loading="placesLoading" class="destination-list">
        <button type="button" class="destination-item" @click="chooseMyLocation">
          <span class="destination-icon" aria-hidden="true">◎</span>
          <span>
            <strong>My location</strong>
            <small>Melbourne central</small>
          </span>
        </button>
        <div v-if="filteredZones.length" class="suggestion-section-label">Tree-density zones</div>
        <button
          v-for="zone in filteredZones"
          :key="zone.id"
          type="button"
          class="destination-item"
          @click="chooseZone(zone)"
        >
          <span class="destination-icon" aria-hidden="true">●</span>
          <span>
            <strong>{{ zone.label }}</strong>
            <small>
              Tree-density zone · {{ zone.density }} · {{ zone.distanceKm.toFixed(1) }} km
            </small>
          </span>
          <b>{{ zone.treeCount }} trees</b>
        </button>
        <div v-if="placeSuggestions.length" class="suggestion-section-label">Google places</div>
        <button
          v-for="place in placeSuggestions"
          :key="place.id"
          type="button"
          class="destination-item"
          @click="choosePlace(place)"
        >
          <span class="destination-icon place-icon" aria-hidden="true">⌖</span>
          <span>
            <strong>{{ place.label }}</strong>
            <small>Google place</small>
          </span>
        </button>
        <p v-if="placesError && activeQuery.length >= 2" class="places-error">
          {{ placesError }}
        </p>
        <ElEmpty
          v-if="
            activeQuery.length >= 2 &&
            !filteredZones.length &&
            !placeSuggestions.length &&
            !placesLoading
          "
          :image-size="54"
          description="No matching areas or places"
        />
        <p v-if="activeQuery.length < 2 && !filteredZones.length" class="autocomplete-hint">
          Type at least 2 characters to search Google places.
        </p>
      </div>

      <template v-else>
        <div v-loading="loading ?? false" class="route-results">
          <ElAlert v-if="error" :title="error" type="error" show-icon :closable="false" />
          <div v-else class="route-options">
            <button
              v-for="option in options"
              :key="option.id"
              class="route-option"
              :class="{ selected: true }"
              type="button"
              @click="emit('select', option.id)"
            >
              <span class="route-symbol" aria-hidden="true">♧</span>
              <span>
                <strong>{{ option.label }}</strong>
                <small>
                  {{ option.durationMinutes }} min · {{ option.distanceKm.toFixed(1) }} km ·
                  {{ option.treeCount }} trees
                </small>
              </span>
            </button>
          </div>
        </div>
        <ElButton class="close-button" text @click="emit('close')">Close directions</ElButton>
      </template>
    </template>
  </section>
</template>

<style scoped>
.route-planner {
  position: absolute;
  z-index: 12;
  top: 22px;
  left: 50%;
  width: min(520px, calc(100% - 500px));
  overflow: hidden;
  border: 1px solid rgb(23 53 29 / 12%);
  border-radius: 18px;
  background: rgb(255 255 255 / 98%);
  box-shadow: 0 14px 38px rgb(31 68 35 / 20%);
  transform: translateX(-50%);
}

.route-planner.collapsed {
  width: fit-content;
  min-width: 220px;
}

.collapsed-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 10px 10px 16px;
  border: 0;
  background: transparent;
  color: var(--tg-text);
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
}

.collapsed-bar span {
  max-width: 220px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.planner-header {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) 42px 36px;
  align-items: start;
  gap: 8px;
  padding: 14px;
  border-bottom: 1px solid rgb(23 53 29 / 9%);
}

.route-inputs {
  position: relative;
  display: grid;
  gap: 12px;
}

.input-connector {
  position: absolute;
  z-index: 1;
  top: 40px;
  left: 17px;
  width: 1px;
  height: 12px;
  background: var(--tg-green-300);
}

.route-inputs :deep(.el-input__wrapper) {
  min-height: 42px;
  background: var(--tg-cream);
  box-shadow: 0 0 0 1px rgb(23 53 29 / 12%) inset;
}

.route-inputs :deep(.el-input:last-child .el-input__wrapper) {
  background: var(--tg-green-50);
  box-shadow: 0 0 0 1px var(--tg-green-500) inset;
}

.swap-button {
  height: 42px;
}

.destination-list {
  max-height: min(460px, calc(100vh - 250px));
  overflow-y: auto;
  padding: 8px 0;
}

.suggestion-section-label {
  padding: 10px 18px 5px;
  color: var(--tg-muted);
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.place-icon {
  color: #337dcc;
}

.places-error {
  margin: 12px 18px;
  color: var(--el-color-danger);
  font-size: 0.7rem;
}

.autocomplete-hint {
  margin: 18px;
  color: var(--tg-muted);
  font-size: 0.7rem;
}

.destination-item {
  display: grid;
  width: 100%;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 13px 18px;
  border: 0;
  background: transparent;
  color: var(--tg-text);
  text-align: left;
  cursor: pointer;
}

.destination-item:hover,
.destination-item:focus-visible {
  background: var(--tg-green-50);
}

.destination-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 10px;
  background: #f0f2ee;
  color: var(--tg-green-700);
}

.destination-item strong,
.destination-item small {
  display: block;
}

.destination-item strong {
  font-size: 0.88rem;
}

.destination-item small {
  margin-top: 4px;
  color: var(--tg-muted);
  font-size: 0.7rem;
}

.destination-item b {
  color: var(--tg-green-700);
  font-size: 0.66rem;
}

.route-options {
  display: grid;
  gap: 8px;
  padding: 14px 14px 0;
}

.route-results {
  min-height: 120px;
  padding: 14px 14px 0;
}

.route-results .route-options {
  padding: 0;
}

.route-option {
  display: grid;
  width: 100%;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 13px 14px;
  border: 1px solid var(--tg-border);
  border-radius: 12px;
  background: white;
  color: var(--tg-text);
  text-align: left;
  cursor: pointer;
}

.route-option.selected {
  border-color: var(--tg-green-700);
  background: var(--tg-green-50);
}

.route-symbol {
  color: var(--tg-green-700);
  font-size: 1.25rem;
}

.route-option strong,
.route-option small {
  display: block;
}

.route-option strong {
  color: var(--tg-green-800);
  font-size: 0.88rem;
}

.route-option small {
  margin-top: 3px;
  color: var(--tg-muted);
  font-size: 0.7rem;
}

.route-option b {
  color: var(--tg-green-700);
  font-size: 0.68rem;
}

.comparison {
  margin: 14px 14px 0;
  color: var(--tg-green-700);
  font-size: 0.72rem;
  font-weight: 700;
  text-align: center;
}

.close-button {
  display: flex;
  margin: 3px auto 8px;
  font-size: 0.7rem;
}

@media (max-width: 900px) {
  .route-planner {
    right: 12px;
    left: auto;
    width: min(470px, calc(100% - 214px));
    transform: none;
  }
}

@media (max-width: 720px) {
  .route-planner {
    top: 10px;
    right: 12px;
    width: calc(100% - 24px);
  }

  .destination-item b {
    display: none;
  }
}
</style>
