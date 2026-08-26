import { precincts, zones } from '@/data/discovery.mock'
import type { NeighbourhoodSnapshot, Precinct, TreeZone } from '@/types/discovery'

export function findPrecinct(query: string): Precinct | undefined {
  const normalized = query.trim().toLocaleLowerCase()
  return precincts.find((precinct) => precinct.name.toLocaleLowerCase() === normalized)
}

export function getPrecinctZones(precinctId: string): TreeZone[] {
  return zones
    .filter((zone) => zone.precinctId === precinctId)
    .sort((first, second) => second.treeCount - first.treeCount)
}

export function getNeighbourhoodSnapshot(precinct: Precinct): NeighbourhoodSnapshot {
  return {
    treeCount: precinct.treeCount,
    zoneCount: getPrecinctZones(precinct.id).length,
    speciesCount: precinct.speciesCount,
  }
}
