import { beforeEach, expect, it, vi } from 'vitest'

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('@/api/client', () => ({ apiGet: get, apiPost: post }))
const precinct = {
  id: 'kensington',
  name: 'Kensington',
  referencePoint: { lat: -37.7934, lng: 144.9305 },
  treeCount: 10,
  zoneCount: 1,
  speciesCount: 2,
}
const zone = {
  id: 'real-zone',
  precinctId: 'kensington',
  center: precinct.referencePoint,
  bounds: { north: -37.79, south: -37.8, east: 144.94, west: 144.93 },
  treeCount: 2,
  density: 'Low',
  dominantGenus: 'Eucalyptus',
  distanceKm: 0.4,
}
beforeEach(() => {
  vi.resetModules()
  vi.stubEnv('VITE_USE_MOCK_DATA', 'false')
  get.mockReset()
  post.mockReset()
})

it('loads existing precinct and Google Places APIs instead of fixture locations', async () => {
  const service = await import('@/services/personalisation.service')
  get.mockResolvedValueOnce([precinct])
  expect(await service.loadPrecincts()).toEqual([precinct])
  expect(get).toHaveBeenLastCalledWith('/api/precincts', undefined)
  get.mockResolvedValueOnce([{ id: 'google-id', label: 'Real address' }])
  expect(await service.searchLocations('Real')).toEqual([
    { id: 'google-id', label: 'Real address' },
  ])
  expect(get).toHaveBeenLastCalledWith('/api/places/autocomplete?query=Real', undefined)
})

it('wraps the legacy map adapter single-object /api/routes response in an array', async () => {
  post.mockResolvedValueOnce({
    id: 'personalised',
    label: 'Walking route',
    durationMinutes: 8,
    distanceKm: 0.6,
    treeCount: 10,
    encodedPolyline: 'live-route',
  })
  const { getWalkingRoutes } = await import('@/services/discovery.service')
  const result = await getWalkingRoutes(precinct.referencePoint, { lat: -37.79, lng: 144.94 })
  expect(result).toEqual([
    {
      id: 'personalised',
      label: 'Walking route',
      durationMinutes: 8,
      distanceKm: 0.6,
      treeCount: 10,
      encodedPolyline: 'live-route',
    },
  ])
  expect(post).toHaveBeenLastCalledWith(
    '/api/routes',
    { origin: precinct.referencePoint, destination: { lat: -37.79, lng: 144.94 }, travelMode: 'WALK' },
    undefined,
  )
})

it('normalises live /api/zones metrics from a 0-100 score to a 0-1 fraction', async () => {
  get.mockImplementation((path: string) =>
    Promise.resolve(
      path.startsWith('/api/zones')
        ? [{ ...zone, metrics: { canopy: 63, parkShare: 4, lowAllergyShare: null, highPollenTrees: null } }]
        : [],
    ),
  )
  const { loadAreas } = await import('@/services/personalisation.service')
  const result = await loadAreas(precinct)
  expect(result[0]?.metrics.canopy).toBeCloseTo(0.63)
  expect(result[0]?.metrics.parkShare).toBeCloseTo(0.04)
})

it('accepts the existing zones/trees contract without inventing new fields', async () => {
  get.mockImplementation((path: string) =>
    Promise.resolve(
      path.startsWith('/api/zones')
        ? [zone]
        : [
            {
              id: '1',
              zoneId: zone.id,
              coordinates: zone.center,
              genus: 'Eucalyptus',
              locatedIn: 'Park',
            },
            {
              id: '2',
              zoneId: zone.id,
              coordinates: zone.center,
              genus: 'Ulmus',
              locatedIn: 'Street',
            },
          ],
    ),
  )
  const { loadAreas } = await import('@/services/personalisation.service')
  const result = await loadAreas(precinct)
  expect(result[0]).toMatchObject({
    id: 'real-zone',
    label: 'Kensington',
    nearestStreet: null,
    treeCount: 2,
    metrics: { parkShare: 0.5, lowAllergyShare: null, highPollenTrees: null },
    genera: [
      { name: 'Eucalyptus', count: 1 },
      { name: 'Ulmus', count: 1 },
    ],
  })
  expect(result[0]?.trees).toHaveLength(2)
})

it('normalises the backend\'s 0-100 metrics scale to the 0-1 fractions the UI expects', async () => {
  // Real backend response shape (verified against the live API): canopy/parkShare
  // are a 0-100 score ("canopy 63, parkShare 4"), not the 0-1 fraction every
  // frontend threshold assumes.
  post.mockResolvedValueOnce({
    id: 'personalised',
    label: 'Personalised walking route',
    travelMode: 'WALK',
    durationMinutes: 12,
    distanceKm: 0.9,
    treeCount: 50,
    encodedPolyline: 'live-route',
    metrics: { canopy: 63, parkShare: 4, lowAllergyShare: null, highPollenTrees: null },
    match: { score: 24, matches: [], sentence: 'Matches your tree canopy.' },
    candidateCount: 2,
    message: null,
  })
  const { requestPersonalisedRoute } = await import('@/services/personalisation.service')
  const input = {
    origin: precinct.referencePoint,
    destination: { lat: -37.79, lng: 144.94 },
    precinctId: 'kensington',
    travelMode: 'WALK' as const,
    preferences: { canopy: 100, shade: null, noise: null, allergy: null, walkingTime: null },
  }
  const result = await requestPersonalisedRoute(input)
  expect(result).toMatchObject({
    id: 'personalised',
    durationMinutes: 12,
    distanceKm: 0.9,
    encodedPolyline: 'live-route',
    isMock: false,
    candidateCount: 2,
  })
  expect(result.metrics?.canopy).toBeCloseTo(0.63)
  expect(result.metrics?.parkShare).toBeCloseTo(0.04)
  expect(post).toHaveBeenLastCalledWith('/api/routes', input)
})

it('never shows environmental scoring for a TRANSIT route', async () => {
  post.mockResolvedValueOnce({
    id: 'personalised',
    label: 'Transport route',
    travelMode: 'TRANSIT',
    durationMinutes: 15,
    distanceKm: 1.1,
    treeCount: 50,
    metrics: null,
    match: null,
    candidateCount: 1,
    message: null,
  })
  const { requestPersonalisedRoute } = await import('@/services/personalisation.service')
  const result = await requestPersonalisedRoute({
    origin: precinct.referencePoint,
    destination: { lat: -37.79, lng: 144.94 },
    precinctId: 'kensington',
    travelMode: 'TRANSIT',
    preferences: { canopy: 100, shade: null, noise: null, allergy: null, walkingTime: null },
  })
  expect(result.metrics).toBeNull()
  expect(result.match).toBeNull()
  expect(result.treeCount).toBe(50)
})
