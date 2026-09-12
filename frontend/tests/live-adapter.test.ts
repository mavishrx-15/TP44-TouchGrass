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

it('preserves live route geometry, distance and time while choosing one legacy alternative', async () => {
  post.mockResolvedValue([
    {
      id: 'fastest',
      label: 'Fastest Route',
      durationMinutes: 8,
      distanceKm: 0.6,
      treeCount: 10,
      encodedPolyline: 'live-fastest',
    },
    {
      id: 'green',
      label: 'Tree-Dense Route',
      durationMinutes: 12,
      distanceKm: 0.9,
      treeCount: 50,
      encodedPolyline: 'live-green',
    },
  ])
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
    encodedPolyline: 'live-green',
    isMock: false,
    scoringPending: true,
  })
  expect(result.path).toBeUndefined()
  expect(result.metrics?.parkShare).toBeNull()
  await expect(requestPersonalisedRoute({ ...input, travelMode: 'TRANSIT' })).rejects.toThrow(
    'Transport is not supported',
  )
})
