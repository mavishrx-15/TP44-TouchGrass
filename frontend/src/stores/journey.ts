import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getPrecincts } from '@/services/discovery.service'
import { nearestPrecinct, withinCoverage } from '@/services/preferences'
import type { Coordinates, Precinct, Preferences, RoutePlace, TravelMode } from '@/types/discovery'

export const useJourneyStore = defineStore('journey', () => {
  const preferences = ref<Preferences>({
    canopy: 3,
    shade: 3,
    noise: 2,
    allergy: 0,
    walkingMinutes: 30,
    avoidGenera: [],
    avoidFamilies: [],
  })
  const startLocation = ref<Coordinates | null>(null)
  const startLocationLabel = ref('')
  const destination = ref<RoutePlace | null>(null)
  const travelMode = ref<TravelMode>('WALK')
  const precincts = ref<Precinct[]>([])
  const loading = ref(false)
  const error = ref('')
  let pending: Promise<void> | undefined
  const covered = computed(
    () => !!startLocation.value && withinCoverage(startLocation.value, precincts.value),
  )
  const originPrecinct = computed(() =>
    startLocation.value ? nearestPrecinct(startLocation.value, precincts.value) : undefined,
  )
  const allergyValid = computed(
    () =>
      !preferences.value.allergy ||
      [...preferences.value.avoidGenera, ...preferences.value.avoidFamilies].some((s) => s.trim()),
  )
  const ready = computed(() => covered.value && allergyValid.value)
  function setStart(place: RoutePlace | null) {
    startLocation.value = place?.coordinates ?? null
    startLocationLabel.value = place?.label ?? ''
  }
  async function initialize() {
    if (precincts.value.length) return
    if (pending) return pending
    loading.value = true
    error.value = ''
    pending = (async () => {
      try {
        precincts.value = await getPrecincts()
      } catch {
        error.value = 'Supported locations could not be loaded. Please retry.'
      } finally {
        loading.value = false
        pending = undefined
      }
    })()
    return pending
  }
  return {
    preferences,
    startLocation,
    startLocationLabel,
    destination,
    travelMode,
    precincts,
    loading,
    error,
    covered,
    originPrecinct,
    allergyValid,
    ready,
    setStart,
    initialize,
  }
})
