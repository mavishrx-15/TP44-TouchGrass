import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { precincts, routeOptions, trees } from '@/data/discovery.mock'
import {
  findPrecinct,
  getNeighbourhoodSnapshot,
  getPrecinctZones,
} from '@/services/discovery.service'
import type { DensityTier, RouteOption, TreeGenus, TreeRecord, TreeZone } from '@/types/discovery'

export const useDiscoveryStore = defineStore('discovery', () => {
  const selectedPrecinct = ref(precincts[0])
  const searchError = ref<string | null>(null)
  const selectedTree = ref<TreeRecord | null>(null)
  const selectedZone = ref<TreeZone | null>(null)
  const selectedRouteId = ref<RouteOption['id']>('green')
  const densityFilters = ref<DensityTier[]>(['High', 'Medium', 'Low'])
  const genusFilters = ref<TreeGenus[]>([])
  const distanceFilter = ref<1 | 3 | 5>(5)

  const snapshot = computed(() => getNeighbourhoodSnapshot(selectedPrecinct.value))
  const rankedZones = computed(() => getPrecinctZones(selectedPrecinct.value.id).slice(0, 3))
  const selectedRoute = computed(
    () => routeOptions.find((route) => route.id === selectedRouteId.value) ?? routeOptions[0],
  )

  function search(query: string): boolean {
    const precinct = findPrecinct(query)
    if (!precinct) {
      searchError.value = `No tree data was found for “${query.trim()}”. Try Kensington, Carlton, North Melbourne or Parkville.`
      return false
    }

    selectedPrecinct.value = precinct
    searchError.value = null
    selectedTree.value = null
    selectedZone.value = null
    return true
  }

  function resetFilters() {
    densityFilters.value = ['High', 'Medium', 'Low']
    genusFilters.value = []
    distanceFilter.value = 5
  }

  return {
    precincts,
    trees,
    routeOptions,
    selectedPrecinct,
    searchError,
    selectedTree,
    selectedZone,
    selectedRouteId,
    selectedRoute,
    densityFilters,
    genusFilters,
    distanceFilter,
    snapshot,
    rankedZones,
    search,
    resetFilters,
  }
})
