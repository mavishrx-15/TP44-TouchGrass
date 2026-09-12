import { apiGet, apiPost } from '@/api/client'
import { distanceKm, getPlaceDetails, getPlaceSuggestions, getPrecincts } from './discovery.service'
import { mockAreas, mockPlaces, mockPrecincts } from './personalisation.mock'
import { COVERAGE_THRESHOLD_KM, scorePreferences, withinBudget } from './preferences'
import type {
  Coordinates,
  PlaceSuggestion,
  Precinct,
  RoutePlace,
  TreeRecord,
  TreeZone,
  RouteOption,
} from '@/types/discovery'
import type {
  Area,
  Coverage,
  PersonalisedRequest,
  PersonalisedRoute,
  Preferences,
  Recommendation,
} from '@/types/personalisation'

// Existing maps, Places, zones and walking routes are LIVE by default.
// Fully mocked data is an explicit fixture mode for isolated UI tests only.
export const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === 'true'
export const MOCK_ACCESS = USE_MOCK_DATA || import.meta.env.VITE_MOCK_ACCESS !== 'false'
export const pause = (ms = 450) => new Promise<void>((resolve) => setTimeout(resolve, ms))

export async function loadPrecincts(): Promise<Precinct[]> {
  if (!USE_MOCK_DATA) return getPrecincts()
  await pause(100)
  return mockPrecincts
}

export function coverageFrom(origin: Coordinates, precincts: Precinct[]): Coverage | null {
  const nearest = precincts
    .filter((p) => p.zoneCount > 0)
    .map((precinct) => ({ precinct, distanceKm: distanceKm(origin, precinct.referencePoint) }))
    .sort((a, b) => a.distanceKm - b.distanceKm)[0]
  return nearest ? { ...nearest, outside: nearest.distanceKm > COVERAGE_THRESHOLD_KM } : null
}

export async function searchLocations(
  query: string,
  signal?: AbortSignal,
): Promise<PlaceSuggestion[]> {
  if (query.trim().length < 2) return []
  if (!USE_MOCK_DATA) return getPlaceSuggestions(query, signal)
  await pause(180)
  if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
  return mockPlaces.filter((place) =>
    place.label.toLowerCase().includes(query.trim().toLowerCase()),
  )
}

export async function resolveLocation(id: string): Promise<RoutePlace> {
  if (!USE_MOCK_DATA) return getPlaceDetails(id)
  await pause(120)
  const place = mockPlaces.find((item) => item.id === id)
  if (!place) throw new Error('Please choose another address.')
  return place
}

export function deviceLocation(): Promise<RoutePlace> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation)
      return reject(
        new Error('Location is unavailable in this browser. Search for an address instead.'),
      )
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          id: 'device',
          label: 'My current location',
          coordinates: { lat: position.coords.latitude, lng: position.coords.longitude },
        }),
      (error) =>
        reject(
          new Error(
            error.code === 1
              ? 'Location permission was declined. You can still search for an address or choose an area.'
              : 'We could not find your location. Please try again or search for an address.',
          ),
        ),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    )
  })
}

export async function loadAreas(precinct: Precinct): Promise<Area[]> {
  if (USE_MOCK_DATA) {
    await pause()
    return mockAreas(precinct)
  }
  const slug = encodeURIComponent(precinct.id)
  const [zones, treeResponse] = await Promise.allSettled([
    apiGet<(TreeZone & Partial<Area>)[]>(`/api/zones?precinct=${slug}&limit=500`),
    apiGet<Omit<TreeRecord, 'distanceKm' | 'mapPosition'>[]>(
      `/api/trees?precinct=${slug}&limit=5000`,
    ),
  ])
  if (zones.status === 'rejected') throw zones.reason
  const trees = treeResponse.status === 'fulfilled' ? treeResponse.value : []
  const grouped = new Map<string, TreeRecord[]>()
  for (const tree of trees) {
    const group = grouped.get(tree.zoneId) ?? []
    group.push({
      ...tree,
      distanceKm: distanceKm(precinct.referencePoint, tree.coordinates),
      mapPosition: { x: 0, y: 0 },
    })
    grouped.set(tree.zoneId, group)
  }
  return zones.value.map((area) => {
    const records = grouped.get(area.id) ?? []
    const complete = records.length === area.treeCount && records.length > 0
    const counts = new Map<string, number>()
    records.forEach((tree) => counts.set(tree.genus, (counts.get(tree.genus) ?? 0) + 1))
    return {
      ...area,
      nearestStreet: area.nearestStreet ?? null,
      precinctName: precinct.name,
      label: area.nearestStreet ? `${precinct.name} · ${area.nearestStreet}` : precinct.name,
      description: area.description ?? `${area.density}-density tree area.`,
      mapPosition: { x: 0, y: 0, width: 0, height: 0 },
      metrics: area.metrics ?? {
        canopy: { High: 0.9, Medium: 0.55, Low: 0.2 }[area.density],
        parkShare: complete
          ? records.filter((tree) => tree.locatedIn === 'Park').length / records.length
          : null,
        lowAllergyShare: null,
        highPollenTrees: null,
      },
      genera:
        area.genera ??
        Array.from(counts, ([name, count]) => ({ name, count }))
          .sort((a, b) => b.count - a.count)
          .slice(0, 3),
      trees: records,
      dataNotes: area.dataNotes ?? [
        'Tree density is used as a canopy proxy; allergy scoring is not yet available.',
        ...(!complete
          ? ['Tree breakdown is incomplete; shade and noise information is unavailable.']
          : ['Shade and noise use park-side tree share, not measured temperature or sound.']),
        ...(!area.nearestStreet ? ['Nearby street has not been supplied yet.'] : []),
      ],
    }
  })
}

export function rankAreas(
  areas: Area[],
  origin: Coordinates,
  preferences: Preferences,
): Recommendation[] {
  return areas
    .map((area) => {
      const km = distanceKm(origin, area.center)
      const estimatedMinutes = Math.max(1, Math.ceil((km / 4.8) * 60))
      return {
        ...area,
        distanceKm: km,
        estimatedMinutes,
        match: scorePreferences(area.metrics, preferences, estimatedMinutes),
      }
    })
    .sort(
      (a, b) =>
        Number(withinBudget(b.estimatedMinutes, preferences.walkingTime)) -
          Number(withinBudget(a.estimatedMinutes, preferences.walkingTime)) ||
        b.match.score - a.match.score ||
        a.distanceKm - b.distanceKm,
    )
}

export function chooseRoute(
  candidates: PersonalisedRoute[],
  preferences: Preferences,
): PersonalisedRoute {
  if (!candidates.length) throw new Error('No route was found. Try a different destination.')
  const eligible = candidates.filter((route) =>
    withinBudget(route.durationMinutes, preferences.walkingTime),
  )
  const pool = eligible.length ? eligible : candidates
  const best = [...pool].sort(
    (a, b) =>
      (b.match?.score ?? 0) - (a.match?.score ?? 0) || a.durationMinutes - b.durationMinutes,
  )[0]!
  const hasTradeoffs = best.match?.matches.some((item) => !item.matched)
  return {
    ...best,
    candidateCount: candidates.length,
    message: !eligible.length
      ? 'No route fits your walking time. This is the best available option; consider a closer destination or a longer walk.'
      : hasTradeoffs
        ? 'No exact match was found. This route offers the closest fit, with the trade-offs shown below.'
        : null,
  }
}

export async function requestPersonalisedRoute(
  input: PersonalisedRequest,
  area?: Area,
): Promise<PersonalisedRoute> {
  if (!USE_MOCK_DATA) {
    type ApiRoute = Omit<RouteOption, 'id'> &
      Partial<Omit<PersonalisedRoute, 'id'>> & { id: string }
    const result = await apiPost<ApiRoute | ApiRoute[]>('/api/routes', input)
    const routes = Array.isArray(result) ? result : [result]
    if (!routes.length) throw new Error('No route was found. Try another destination.')
    if (input.travelMode === 'TRANSIT') {
      const transit = routes.find((route) => route.travelMode === 'TRANSIT')
      // The old backend silently ignores travelMode. Never show its WALK result as TRANSIT.
      if (!transit)
        throw new Error(
          'Transport is not supported by the current route service yet. Switch back to Walking, or open transport directions in Google Maps.',
        )
      return {
        ...transit,
        id: 'personalised',
        travelMode: 'TRANSIT',
        match: null,
        metrics: null,
        candidateCount: transit.candidateCount ?? 1,
        message: transit.message ?? null,
        isMock: false,
      }
    }
    const ready = routes.find(
      (route) => route.travelMode === 'WALK' && route.match && route.metrics,
    )
    if (ready && routes.length === 1)
      return {
        ...ready,
        id: 'personalised',
        travelMode: 'WALK',
        match: ready.match!,
        metrics: ready.metrics!,
        candidateCount: ready.candidateCount ?? 1,
        message: ready.message ?? null,
        isMock: false,
      }
    const maxTrees = Math.max(1, ...routes.map((route) => route.treeCount))
    const candidates: PersonalisedRoute[] = routes.map((route) => {
      const metrics = {
        canopy: route.treeCount / maxTrees,
        parkShare: null,
        lowAllergyShare: null,
        highPollenTrees: null,
      }
      return {
        ...route,
        id: 'personalised',
        label: 'Walking route',
        travelMode: 'WALK',
        match: scorePreferences(metrics, input.preferences, route.durationMinutes),
        metrics,
        candidateCount: routes.length,
        message: null,
        isMock: false,
        scoringPending: true,
      }
    })
    const chosen = chooseRoute(candidates, input.preferences)
    return {
      ...chosen,
      message: [
        chosen.message,
        'Live Google walking route. Selection currently uses tree counts and walking time; shade, noise and allergy route scoring are not connected yet.',
      ]
        .filter(Boolean)
        .join(' '),
    }
  }
  await pause(650)
  const km = distanceKm(input.origin, input.destination)
  if (km < 0.01) throw new Error('Choose a destination different from your starting point.')
  const metrics = area?.metrics ?? {
    canopy: 0.76,
    parkShare: 0.6,
    lowAllergyShare: null,
    highPollenTrees: null,
  }
  const route = (alternative: number): PersonalisedRoute => {
    const isTransit = input.travelMode === 'TRANSIT'
    const routeKm = km * (isTransit ? 1.35 : 1.2 + alternative * 0.2)
    const durationMinutes = Math.max(
      1,
      Math.ceil((routeKm / (isTransit ? 18 : 4.8)) * 60) + (isTransit ? 5 : 0),
    )
    const scored = {
      ...metrics,
      canopy: metrics.canopy === null ? null : Math.max(0, metrics.canopy - alternative * 0.23),
      parkShare:
        metrics.parkShare === null ? null : Math.min(1, metrics.parkShare + alternative * 0.13),
    }
    return {
      id: 'personalised',
      label: isTransit ? 'Transport route' : 'Personalised walking route',
      travelMode: input.travelMode,
      durationMinutes,
      distanceKm: routeKm,
      treeCount: area?.treeCount ?? 96,
      metrics: isTransit ? null : scored,
      match: isTransit ? null : scorePreferences(scored, input.preferences, durationMinutes),
      candidateCount: isTransit ? 1 : 2,
      message: null,
      isMock: true,
      path: [
        input.origin,
        {
          lat:
            input.origin.lat +
            (input.destination.lat - input.origin.lat) * (alternative ? 0.65 : 0.45),
          lng: input.origin.lng,
        },
        {
          lat:
            input.origin.lat +
            (input.destination.lat - input.origin.lat) * (alternative ? 0.65 : 0.45),
          lng: input.destination.lng,
        },
        input.destination,
      ],
    }
  }
  if (input.travelMode === 'TRANSIT') return route(0)
  return chooseRoute([route(0), route(1)], input.preferences)
}
