import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { distanceKm, zoneLabel } from '@/services/discovery.service'
import { rankRecommendations, withinCoverage } from '@/services/preferences'
import { useJourneyStore } from '@/stores/journey'
import { apiGet, apiPost, clearAccessToken, getAccessToken, setAccessToken } from '@/api/client'
import type { Precinct, Preferences, TreeZone } from '@/types/discovery'

const basePreferences: Preferences = {
  canopy: 0,
  shade: 0,
  noise: 0,
  allergy: 0,
  walkingMinutes: 30,
  avoidGenera: [],
  avoidFamilies: [],
}
const origin = { lat: -37.795, lng: 144.915 }
const precinct: Precinct = {
  id: 'kensington',
  name: 'Kensington',
  referencePoint: origin,
  treeCount: 10,
  speciesCount: 2,
  zoneCount: 2,
}
const zone = (id: string, trees: number, locatedIn: string, genus: string): TreeZone => ({
  id,
  precinctId: 'kensington',
  label: id,
  center: origin,
  bounds: { north: 0, south: 0, east: 0, west: 0 },
  treeCount: trees,
  density: 'High',
  dominantGenus: null,
  distanceKm: 99,
  nearestStreet: null,
  description: '',
  mapPosition: { x: 0, y: 0, width: 0, height: 0 },
  treeProfile: [{ genus, family: 'Family', locatedIn, count: trees }],
})
const token = (seconds: number) =>
  `${btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds })).replace(/=/g, '')}.signature`
beforeEach(() => {
  setActivePinia(createPinia())
  sessionStorage.clear()
  vi.stubGlobal('scrollTo', vi.fn())
  vi.stubGlobal('localStorage', { length: 0, setItem: vi.fn() })
})
afterEach(() => {
  clearAccessToken()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('access lifecycle', () => {
  it('uses session storage and rejects malformed and expired tokens', () => {
    setAccessToken(token(100))
    expect(getAccessToken()).not.toBeNull()
    expect(localStorage.length).toBe(0)
    sessionStorage.setItem('touchgrass_access_token', token(-1))
    expect(getAccessToken()).toBeNull()
    sessionStorage.setItem('touchgrass_access_token', 'nonsense')
    expect(getAccessToken()).toBeNull()
  })
  it('expires even without an API call or route change', () => {
    vi.useFakeTimers()
    const expired = vi.fn()
    window.addEventListener('access-expired', expired, { once: true })
    setAccessToken(token(2))
    vi.advanceTimersByTime(2100)
    expect(getAccessToken()).toBeNull()
    expect(expired).toHaveBeenCalledOnce()
  })
  it('sends bearer tokens on GET and POST and clears on 401', async () => {
    setAccessToken(token(100))
    const fetchMock = vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(
          new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } }),
        ),
      )
    vi.stubGlobal('fetch', fetchMock)
    await apiGet('/api/precincts')
    await apiPost('/api/routes', {})
    expect(
      fetchMock.mock.calls.every((call) => call[1].headers.Authorization.startsWith('Bearer ')),
    ).toBe(true)
    fetchMock.mockResolvedValue(new Response('{}', { status: 401 }))
    await expect(apiGet('/api/precincts')).rejects.toMatchObject({ status: 401 })
    expect(getAccessToken()).toBeNull()
  })
})

describe('preferences and origin', () => {
  it('shares the resolved origin and invalidates it when edited', () => {
    const journey = useJourneyStore()
    journey.precincts = [precinct]
    journey.setStart({ id: 'chosen', label: 'Chosen address', coordinates: origin })
    expect(useJourneyStore().startLocationLabel).toBe('Chosen address')
    expect(journey.ready).toBe(true)
    journey.setStart(null)
    expect(journey.ready).toBe(false)
  })
  it('requires an allergy avoidance category when weighted', () => {
    const journey = useJourneyStore()
    journey.preferences.allergy = 5
    expect(journey.allergyValid).toBe(false)
    journey.preferences.avoidFamilies = ['Myrtaceae']
    expect(journey.allergyValid).toBe(true)
  })
  it('checks haversine coverage on both sides of the configured boundary', () => {
    const point = { lat: origin.lat + 0.01, lng: origin.lng }
    const exact = distanceKm(point, origin)
    expect(withinCoverage(point, [precinct], exact + 0.00001)).toBe(true)
    expect(withinCoverage(point, [precinct], exact - 0.00001)).toBe(false)
    expect(withinCoverage(origin, [])).toBe(false)
    expect(distanceKm(origin, origin)).toBe(0)
  })
  it('uses street names and falls back to precinct alone', () => {
    expect(zoneLabel('north-melbourne', 'Errol Street')).toBe('North Melbourne · Errol Street')
    expect(zoneLabel('north-melbourne', null)).toBe('North Melbourne')
  })
  it('changes ranking for canopy, parks and avoidance, using the real origin distance', () => {
    const zones = [zone('dense', 100, 'Street', 'Acacia'), zone('park', 20, 'Park', 'Ulmus')]
    expect(rankRecommendations(zones, origin, { ...basePreferences, canopy: 5 })[0]?.id).toBe(
      'dense',
    )
    expect(rankRecommendations(zones, origin, { ...basePreferences, shade: 5 })[0]?.id).toBe('park')
    expect(
      rankRecommendations(zones, origin, {
        ...basePreferences,
        allergy: 5,
        avoidGenera: ['Acacia'],
      })[0]?.id,
    ).toBe('park')
    expect(rankRecommendations(zones, origin, basePreferences)[0]?.distanceKm).toBe(0)
    expect(
      rankRecommendations(zones, { ...origin, lat: origin.lat + 0.1 }, basePreferences)[0]
        ?.distanceKm,
    ).toBeGreaterThan(10)
  })
})

describe('route guard', () => {
  it('protects direct links, permits valid sessions and redirects expired sessions', async () => {
    const { default: router } = await import('@/router')
    await router.push('/tree-explorer')
    expect(router.currentRoute.value.name).toBe('access')
    expect(router.currentRoute.value.query.redirect).toBe('/tree-explorer')
    setAccessToken(token(100))
    await router.push('/')
    expect(router.currentRoute.value.name).toBe('home')
    sessionStorage.setItem('touchgrass_access_token', token(-1))
    await router.push('/map')
    expect(router.currentRoute.value.name).toBe('access')
  })
})
