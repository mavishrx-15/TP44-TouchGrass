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

it("normalises the backend's 0-100 metrics scale to the 0-1 fractions the UI expects", async () => {
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
