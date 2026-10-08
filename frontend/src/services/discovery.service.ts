import { apiGet } from '@/api/client'
import type { PlaceSuggestion, Precinct, RoutePlace, TreeRecord, TreeZone } from '@/types/discovery'

type ApiZone = Omit<TreeZone, 'label' | 'description' | 'mapPosition' | 'nearestStreet'> & {
  nearestStreet?: string | null
}

export function getPrecincts(signal?: AbortSignal): Promise<Precinct[]> {
  return apiGet<Precinct[]>('/api/precincts', signal)
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
  // Add display-only fields here so API responses stay focused on domain data.
  const precinctName = precinctId
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
  return result.map((zone) => ({
    ...zone,
    nearestStreet: zone.nearestStreet ?? null,
    label: zone.nearestStreet ? `${precinctName} · ${zone.nearestStreet}` : precinctName,
    description: `${zone.density}-density tree cluster${zone.dominantGenus ? ` dominated by ${zone.dominantGenus}` : ''}.`,
    mapPosition: { x: 0, y: 0, width: 0, height: 0 },
  }))
}

export function distanceKm(
  from: Precinct['referencePoint'],
  to: TreeRecord['coordinates'],
): number {
  // Haversine formula: great-circle distance between two coordinates in kilometres.
  const radians = (degrees: number) => (degrees * Math.PI) / 180
  const latitude = radians(to.lat - from.lat)
  const longitude = radians(to.lng - from.lng)
  const value =
    Math.sin(latitude / 2) ** 2 +
    Math.cos(radians(from.lat)) * Math.cos(radians(to.lat)) * Math.sin(longitude / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, value))))
}
