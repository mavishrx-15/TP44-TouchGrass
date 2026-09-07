import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  findPrecinct,
  getPrecincts,
  getPrecinctTrees,
  getPrecinctZones,
  getSpecies,
  getWalkingRoutes,
} from '@/services/discovery.service'
import type {
  Coordinates,
  DensityTier,
  Precinct,
  RouteOption,
  TreeGenus,
  TreeRecord,
  TreeZone,
} from '@/types/discovery'

const initialPrecinct: Precinct = {
  id: 'kensington',
  name: 'Kensington',
  referencePoint: { lat: -37.7934, lng: 144.9305 },
  treeCount: 0,
  zoneCount: 0,
  speciesCount: 0,
}

export const useDiscoveryStore = defineStore('discovery', () => {
  // Core map data: trees and zones always belong to the selected precinct.
  const precincts = ref<Precinct[]>([])
  const trees = ref<TreeRecord[]>([])
  const zones = ref<TreeZone[]>([])
  const availableGenera = ref<TreeGenus[]>([])
  const selectedPrecinct = ref(initialPrecinct)
  const searchError = ref<string | null>(null)
  const loadError = ref<string | null>(null)
  const isLoading = ref(false)
  const initialized = ref(false)
  const selectedTree = ref<TreeRecord | null>(null)
  const selectedZone = ref<TreeZone | null>(null)
  const routeOptions = ref<RouteOption[]>([])
  const selectedRouteId = ref<RouteOption['id']>('fastest')
  const routesLoading = ref(false)
  const routeError = ref<string | null>(null)
  const densityFilters = ref<DensityTier[]>(['High', 'Medium', 'Low'])
  const genusFilters = ref<TreeGenus[]>([])

  const snapshot = computed(() => ({
    treeCount: selectedPrecinct.value.treeCount,
    zoneCount: selectedPrecinct.value.zoneCount,
    speciesCount: selectedPrecinct.value.speciesCount,
  }))
  const rankedZones = computed(() => zones.value)
  const selectedRoute = computed(
    () =>
      routeOptions.value.find((route) => route.id === selectedRouteId.value) ??
      routeOptions.value[0],
  )

  async function initialize() {
    // Avoid duplicate startup requests when multiple views mount together.
    if (initialized.value || isLoading.value) return
    isLoading.value = true
    loadError.value = null
    try {
      const [loadedPrecincts, species] = await Promise.all([getPrecincts(), getSpecies()])
      precincts.value = loadedPrecincts
      availableGenera.value = species.map((item) => item.genus)
      const initial =
        findPrecinct(loadedPrecincts, selectedPrecinct.value.name) ?? loadedPrecincts[0]
      if (!initial) throw new Error('The API returned no precincts.')
      await selectPrecinct(initial)
      initialized.value = true
    } catch (error) {
      loadError.value = apiErrorMessage(error)
    } finally {
      isLoading.value = false
    }
  }

  async function selectPrecinct(precinct: Precinct) {
    // Commit the precinct only after both requests succeed to keep map data consistent.
    const [loadedZones, loadedTrees] = await Promise.all([
      getPrecinctZones(precinct.id),
      getPrecinctTrees(precinct),
    ])
    selectedPrecinct.value = precinct
    zones.value = loadedZones
    trees.value = loadedTrees
    searchError.value = null
    selectedTree.value = null
    selectedZone.value = null
  }

  async function search(query: string): Promise<boolean> {
    const precinct = findPrecinct(precincts.value, query)
    if (!precinct) {
      searchError.value = `No tree data was found for “${query.trim()}”. Choose a listed Melbourne precinct.`
      return false
    }

    isLoading.value = true
    loadError.value = null
    try {
      await selectPrecinct(precinct)
      return true
    } catch (error) {
      loadError.value = apiErrorMessage(error)
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function planRoutes(origin: Coordinates, destination: Coordinates): Promise<boolean> {
    routesLoading.value = true
    routeError.value = null
    try {
      routeOptions.value = await getWalkingRoutes(origin, destination)
      selectedRouteId.value = 'fastest'
      return true
    } catch (error) {
      routeOptions.value = []
      routeError.value = apiErrorMessage(error).replace('Tree data', 'Routes')
      return false
    } finally {
      routesLoading.value = false
    }
  }

  function resetFilters() {
    densityFilters.value = ['High', 'Medium', 'Low']
    genusFilters.value = []
  }

  function apiErrorMessage(error: unknown) {
    const detail = error instanceof Error ? error.message : 'Unknown error'
    return `Tree data could not be loaded from the API. Check that the backend is running. (${detail})`
  }

  return {
    precincts,
    trees,
    zones,
    availableGenera,
    routeOptions,
    routesLoading,
    routeError,
    selectedPrecinct,
    searchError,
    loadError,
    isLoading,
    initialized,
    selectedTree,
    selectedZone,
    selectedRouteId,
    selectedRoute,
    densityFilters,
    genusFilters,
    snapshot,
    rankedZones,
    initialize,
    search,
    planRoutes,
    resetFilters,
  }
})
