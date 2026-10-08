import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { emptyPreferences } from '@/types/personalisation'
import type { JourneyContext, PersonalisedRoute, TravelMode } from '@/types/personalisation'
import type { Precinct, RoutePlace } from '@/types/discovery'
import type { AreaOption, PlannedRoute } from '@/types/planning'
import {
  coverageFrom,
  deviceLocation,
  loadPrecincts,
  requestPersonalisedRoute,
  USE_MOCK_DATA,
} from '@/services/personalisation.service'
import { findAreas, growRoute } from '@/services/planning.service'
import { preferenceChips } from '@/services/preferences'
import { friendlyError } from '@/data/walkMessages'
import { ApiError } from '@/api/client'

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
  const route = ref<PersonalisedRoute | null>(null)
  const travelMode = ref<TravelMode>('WALK')
  const loading = ref(false)
  const error = ref<string | null>(null)
  const coverage = computed(() =>
    startLocation.value ? coverageFrom(startLocation.value.coordinates, precincts.value) : null,
  )
  const summary = computed(() => preferenceChips(preferences.value))

  // Sprout's own route and areas (POST /api/sprout/route, POST /api/sprout/areas).
  // Kept apart from `route`/`areas`/`recommendations` above, which still back the
  // older Explore page on /api/routes - the two endpoints return different
  // shapes, and a user can have both pages open in one session.
  const sproutRoute = ref<PlannedRoute | null>(null)
  const sproutRouteLoading = ref(false)
  const sproutRouteError = ref<string | null>(null)
  const sproutAreas = ref<AreaOption[]>([])
  const sproutAreasLoading = ref(false)
  const sproutAreasError = ref<string | null>(null)
  let areasSequence = 0

  /** Grows Sprout's route. The backend chooses the destination; this sets it from the response. */
  async function growSproutRoute(destinationZoneId?: string): Promise<boolean> {
    if (sproutRouteLoading.value) return false
    if (!startLocation.value) {
      sproutRouteError.value = 'Choose a starting location first.'
      return false
    }
    sproutRouteLoading.value = true
    sproutRouteError.value = null
    try {
      const result = await growRoute(
        startLocation.value.coordinates,
        preferences.value,
        undefined,
        destinationZoneId,
      )
      sproutRoute.value = result
      destination.value = {
        id: result.destination.zoneId,
        label: result.destination.label,
        coordinates: result.destination.center,
      }
      return true
    } catch (e) {
      const fallback =
        'The next route could not be loaded. Try this area again or choose another nearby area.'
      sproutRouteError.value =
        e instanceof ApiError && e.status !== 401 ? fallback : friendlyError(e, fallback)
      return false
    } finally {
      sproutRouteLoading.value = false
    }
  }

  /** "See other options" / "Find more trees near you" - same ranking the route itself uses. */
  async function findSproutAreas(
    options: { excludedZoneIds?: string[]; limit?: number } = {},
  ): Promise<AreaOption[]> {
    if (!startLocation.value) return []
    const request = ++areasSequence
    sproutAreasLoading.value = true
    sproutAreasError.value = null
    try {
      const result = await findAreas(startLocation.value.coordinates, preferences.value, options)
      if (request !== areasSequence) return []
      sproutAreas.value = result.areas
      return result.areas
    } catch (e) {
      if (request === areasSequence)
        sproutAreasError.value = e instanceof Error ? e.message : 'Areas could not be loaded.'
      return []
    } finally {
      if (request === areasSequence) sproutAreasLoading.value = false
    }
  }

  const cache = new Map<string, PersonalisedRoute>()
  let sequence = 0
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

  async function useCurrentLocation() {
    startLocation.value = await deviceLocation()
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
      const result = await requestPersonalisedRoute(input)
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

  return {
    preferences,
    startLocation,
    destination,
    precincts,
    route,
    travelMode,
    loading,
    error,
    coverage,
    summary,
    sproutRoute,
    sproutRouteLoading,
    sproutRouteError,
    sproutAreas,
    sproutAreasLoading,
    sproutAreasError,
    initialize,
    useCurrentLocation,
    calculate,
    growSproutRoute,
    findSproutAreas,
  }
})
