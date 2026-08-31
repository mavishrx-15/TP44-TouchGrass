import { apiGet, apiPost } from '@/api/client'
import type {
  Coordinates,
  PlaceSuggestion,
  Precinct,
  RouteOption,
  RoutePlace,
  TreeGenus,
  TreeRecord,
  TreeZone,
} from '@/types/discovery'

export interface GenusSummary {
  genus: TreeGenus
  treeCount: number
}

type ApiZone = Omit<TreeZone, 'label' | 'description' | 'mapPosition'>
type ApiTree = Omit<TreeRecord, 'distanceKm' | 'mapPosition'>

export function findPrecinct(precincts: Precinct[], query: string): Precinct | undefined {
  const normalized = query.trim().toLocaleLowerCase()
  return precincts.find((precinct) => precinct.name.toLocaleLowerCase() === normalized)
}

export function getPrecincts(signal?: AbortSignal): Promise<Precinct[]> {
  return apiGet<Precinct[]>('/api/precincts', signal)
}

export function getSpecies(signal?: AbortSignal): Promise<GenusSummary[]> {
  return apiGet<GenusSummary[]>('/api/species', signal)
}

export function getWalkingRoutes(
  origin: Coordinates,
  destination: Coordinates,
  signal?: AbortSignal,
): Promise<RouteOption[]> {
  return apiPost<RouteOption[]>('/api/routes', { origin, destination }, signal)
}

export function getPlaceSuggestions(
  query: string,
  signal?: AbortSignal,
): Promise<PlaceSuggestion[]> {
  return apiGet<PlaceSuggestion[]>(
    `/api/places/autocomplete?query=${encodeURIComponent(query)}`,
    signal,
  )
}

export function getPlaceDetails(placeId: string, signal?: AbortSignal): Promise<RoutePlace> {
  return apiGet<RoutePlace>(`/api/places/${encodeURIComponent(placeId)}`, signal)
}

export async function getPrecinctZones(
  precinctId: string,
  limit = 500,
  signal?: AbortSignal,
): Promise<TreeZone[]> {
  const result = await apiGet<ApiZone[]>(
    `/api/zones?precinct=${encodeURIComponent(precinctId)}&limit=${limit}`,
    signal,
  )
  return result.map((zone, index) => ({
    ...zone,
    label: `Zone ${String(index + 1).padStart(2, '0')}`,
    description: `${zone.density}-density tree cluster${zone.dominantGenus ? ` dominated by ${zone.dominantGenus}` : ''}.`,
    mapPosition: { x: 0, y: 0, width: 0, height: 0 },
  }))
}

export async function getPrecinctTrees(
  precinct: Precinct,
  signal?: AbortSignal,
): Promise<TreeRecord[]> {
  const result = await apiGet<ApiTree[]>(
    `/api/trees?precinct=${encodeURIComponent(precinct.id)}&limit=500`,
    signal,
  )
  return result.map((tree) => ({
    ...tree,
    distanceKm: distanceKm(precinct.referencePoint, tree.coordinates),
    mapPosition: { x: 0, y: 0 },
  }))
}

function distanceKm(from: Precinct['referencePoint'], to: TreeRecord['coordinates']): number {
  const radians = (degrees: number) => (degrees * Math.PI) / 180
  const latitude = radians(to.lat - from.lat)
  const longitude = radians(to.lng - from.lng)
  const value =
    Math.sin(latitude / 2) ** 2 +
    Math.cos(radians(from.lat)) * Math.cos(radians(to.lat)) * Math.sin(longitude / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(value))
}
