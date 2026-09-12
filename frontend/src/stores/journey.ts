import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { emptyPreferences } from '@/types/personalisation'
import type { Area, JourneyContext, PersonalisedRoute, TravelMode } from '@/types/personalisation'
import type { Precinct, RoutePlace } from '@/types/discovery'
import {
  coverageFrom,
  deviceLocation,
  loadAreas,
  loadPrecincts,
  rankAreas,
  requestPersonalisedRoute,
  USE_MOCK_DATA,
} from '@/services/personalisation.service'
import { preferenceChips } from '@/services/preferences'

// Fixture destinations must not leak into a live-data session.
const STORAGE_KEY = USE_MOCK_DATA ? 'touchgrass.journey.v2' : 'touchgrass.journey.live.v1'
function restore(): JourneyContext {
  const fallback = { preferences: emptyPreferences(), startLocation: null, destination: null }
  try {
    const parsed = JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? 'null')
    if (!parsed?.preferences) return fallback
    const p = parsed.preferences
    const slider = (v: unknown) => (typeof v === 'number' && v >= 0 && v <= 100 ? v : null)
    const location = (v: RoutePlace | null) =>
      v &&
      typeof v.label === 'string' &&
      typeof v.id === 'string' &&
      Number.isFinite(v.coordinates?.lat) &&
      Number.isFinite(v.coordinates?.lng)
        ? v
        : null
    return {
      preferences: {
        canopy: slider(p.canopy),
        shade: slider(p.shade),
        noise: ['quiet', 'lively'].includes(p.noise) ? p.noise : null,
        allergy: ['avoid', 'lower'].includes(p.allergy) ? p.allergy : null,
        walkingTime: [5, 10, 15, 20].includes(p.walkingTime) ? p.walkingTime : null,
      },
      startLocation: location(parsed.startLocation),
      destination: location(parsed.destination),
    }
  } catch {
    return fallback
  }
}

export const useJourneyStore = defineStore('journey', () => {
  const saved = restore()
  const preferences = ref(saved.preferences)
  const startLocation = ref(saved.startLocation)
  const destination = ref(saved.destination)
  const precincts = ref<Precinct[]>([])
  const areas = ref<Area[]>([])
  const route = ref<PersonalisedRoute | null>(null)
  const travelMode = ref<TravelMode>('WALK')
  const loading = ref(false)
  const areasLoading = ref(false)
  const error = ref<string | null>(null)
  const areaError = ref<string | null>(null)
  const coverage = computed(() =>
    startLocation.value ? coverageFrom(startLocation.value.coordinates, precincts.value) : null,
  )
  const summary = computed(() => preferenceChips(preferences.value))
  const recommendations = computed(() =>
    startLocation.value
      ? rankAreas(areas.value, startLocation.value.coordinates, preferences.value)
      : [],
  )
  const selectedArea = computed(() => areas.value.find((area) => area.id === destination.value?.id))
  const cache = new Map<string, PersonalisedRoute>()
  let sequence = 0
  let areaSequence = 0
  let initPromise: Promise<void> | null = null

  function initialize() {
    if (precincts.value.length) return Promise.resolve()
    if (!initPromise)
      initPromise = loadPrecincts()
        .then((value) => {
          precincts.value = value
        })
        .finally(() => {
          initPromise = null
        })
    return initPromise
  }

  watch(
    [preferences, startLocation, destination],
    () => {
      sequence++
      loading.value = false
      route.value = null
      error.value = null
      cache.clear()
      try {
        sessionStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({
            preferences: preferences.value,
            startLocation: startLocation.value,
            destination: destination.value,
          }),
        )
      } catch {
        /* Preference persistence is optional. */
      }
    },
    { deep: true, flush: 'sync' },
  )

  function skipPersonalisation() {
    preferences.value = { ...emptyPreferences(), walkingTime: preferences.value.walkingTime }
  }

  async function useCurrentLocation() {
    startLocation.value = await deviceLocation()
  }

  async function refreshAreas() {
    const request = ++areaSequence
    areasLoading.value = true
    areaError.value = null
    areas.value = []
    try {
      await initialize()
      const precinct = coverage.value?.precinct
      if (!precinct) throw new Error('Choose a starting location to find nearby areas.')
      const result = await loadAreas(precinct)
      if (request === areaSequence) areas.value = result
    } catch (e) {
      if (request === areaSequence)
        areaError.value = e instanceof Error ? e.message : 'Areas could not be loaded.'
    } finally {
      if (request === areaSequence) areasLoading.value = false
    }
  }

  async function calculate(mode: TravelMode = travelMode.value) {
    const request = ++sequence
    travelMode.value = mode
    error.value = null
    route.value = null
    if (!startLocation.value || !destination.value) {
      error.value = 'Choose a starting location and a destination first.'
      return false
    }
    const input = {
      origin: { ...startLocation.value.coordinates },
      destination: { ...destination.value.coordinates },
      preferences: { ...preferences.value },
      travelMode: mode,
      precinctId: coverage.value?.precinct.id ?? '',
    }
    const key = JSON.stringify(input)
    const cached = cache.get(key)
    if (cached) {
      route.value = cached
      return true
    }
    loading.value = true
    try {
      const result = await requestPersonalisedRoute(input, selectedArea.value)
      if (request !== sequence) return false
      cache.set(key, result)
      route.value = result
      return true
    } catch (e) {
      if (request === sequence)
        error.value = e instanceof Error ? e.message : 'The route could not be calculated.'
      return false
    } finally {
      if (request === sequence) loading.value = false
    }
  }

  async function findGreenerRoute() {
    if (!startLocation.value) return false
    await refreshAreas()
    const best = recommendations.value[0]
    if (!best) {
      error.value = areaError.value ?? 'No areas were found nearby. Try another starting point.'
      return false
    }
    destination.value = { id: best.id, label: best.label, coordinates: best.center }
    return calculate('WALK')
  }

  return {
    preferences,
    startLocation,
    destination,
    precincts,
    areas,
    route,
    travelMode,
    loading,
    areasLoading,
    error,
    areaError,
    coverage,
    summary,
    recommendations,
    selectedArea,
    initialize,
    skipPersonalisation,
    useCurrentLocation,
    refreshAreas,
    calculate,
    findGreenerRoute,
  }
})
