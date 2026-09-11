import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { emptyPreferences } from '@/types/personalisation'
import { scorePreferences, withinBudget } from '@/services/preferences'
import {
  chooseRoute,
  coverageFrom,
  rankAreas,
  requestPersonalisedRoute,
} from '@/services/personalisation.service'
import { mockAreas, mockPrecincts } from '@/services/personalisation.mock'
import { distanceKm } from '@/services/discovery.service'
import { useJourneyStore } from '@/stores/journey'
import { DEMO_PASSWORD, getAccessToken, verifyAccess } from '@/services/access.service'

beforeEach(() => {
  const memory = new Map<string, string>()
  vi.stubGlobal('sessionStorage', {
    getItem: (key: string) => memory.get(key) ?? null,
    setItem: (key: string, value: string) => memory.set(key, value),
    removeItem: (key: string) => memory.delete(key),
    clear: () => memory.clear(),
  })
  setActivePinia(createPinia())
})

describe('shared preference matching', () => {
  const metrics = { canopy: 0.92, parkShare: 0.2, lowAllergyShare: 0.7, highPollenTrees: 2 }
  it('unset preferences add no score; selected dimensions stay independent', () => {
    expect(scorePreferences(metrics, emptyPreferences(), 11)).toMatchObject({
      score: 0,
      matches: [],
    })
    const canopy = scorePreferences(metrics, { ...emptyPreferences(), canopy: 100 }, 11)
    expect(canopy.matches[0]).toMatchObject({
      key: 'canopy',
      matched: true,
      detail: 'High tree canopy',
    })
    const multiple = scorePreferences(
      metrics,
      { ...emptyPreferences(), canopy: 100, noise: 'quiet' },
      11,
    )
    expect(multiple.matches[0]).toEqual(canopy.matches[0])
    expect(multiple.matches[1]).toMatchObject({ key: 'noise', matched: false })
    expect(multiple.score).toBeCloseTo((0.92 + 0.2) / 2)
  })
  it('does not label missing allergy information as a match', () => {
    const result = scorePreferences(
      { ...metrics, lowAllergyShare: null, highPollenTrees: null },
      { ...emptyPreferences(), allergy: 'lower' },
      11,
    )
    expect(result.matches[0]?.matched).toBe(false)
    expect(result.matches[0]?.detail).toContain('not yet confirmed')
  })
  it('handles time tolerance and the open-ended 20+ option', () => {
    expect(withinBudget(17, 15)).toBe(true)
    expect(withinBudget(18, 15)).toBe(false)
    expect(withinBudget(45, 20)).toBe(true)
  })
})

describe('real origin and recommendations', () => {
  it('computes distance from the resolved origin and changes ordering when it moves', () => {
    const areas = mockAreas(mockPrecincts[1]!)
    const first = rankAreas(areas, areas[0]!.center, emptyPreferences())
    const second = rankAreas(areas, areas[1]!.center, emptyPreferences())
    expect(first[0]?.id).toBe(areas[0]!.id)
    expect(second[0]?.id).toBe(areas[1]!.id)
    expect(first[0]?.distanceKm).toBe(0)
    expect(areas[2]?.nearestStreet).toBeNull()
    expect(areas[2]?.label).toBe('Kensington')
  })
  it('finds the nearest covered precinct and only warns outside the threshold', () => {
    expect(coverageFrom(mockPrecincts[1]!.referencePoint, mockPrecincts)?.outside).toBe(false)
    const outside = coverageFrom({ lat: -38.1447, lng: 144.3556 }, mockPrecincts)
    expect(outside?.outside).toBe(true)
    expect(outside!.distanceKm).toBeGreaterThan(40)
    expect(distanceKm({ lat: 0, lng: 0 }, { lat: 0, lng: 180 })).toBeCloseTo(20015, 0)
  })
})

describe('single-route selection and mode switch', () => {
  it('returns one route; excludes over-budget alternatives, and explains fallback', async () => {
    const input = {
      origin: mockPrecincts[1]!.referencePoint,
      destination: mockAreas(mockPrecincts[1]!)[0]!.center,
      preferences: { ...emptyPreferences(), canopy: 100 },
      travelMode: 'WALK' as const,
      precinctId: 'kensington',
    }
    const result = await requestPersonalisedRoute(input)
    const slow = { ...result, durationMinutes: 35, match: { ...result.match!, score: 1 } }
    const quick = { ...result, durationMinutes: 8, match: { ...result.match!, score: 0.4 } }
    expect(
      chooseRoute([slow, quick], { ...input.preferences, walkingTime: 10 }).durationMinutes,
    ).toBe(8)
    expect(chooseRoute([slow], { ...input.preferences, walkingTime: 5 }).message).toContain(
      'No route fits',
    )
    expect(chooseRoute([quick], input.preferences).candidateCount).toBe(1)
  })
  it('replaces the walking route with transit and restores the cached walk', async () => {
    const store = useJourneyStore()
    store.startLocation = {
      id: 'start',
      label: 'Kensington',
      coordinates: mockPrecincts[1]!.referencePoint,
    }
    store.destination = {
      id: 'end',
      label: 'Macaulay Rd',
      coordinates: mockAreas(mockPrecincts[1]!)[0]!.center,
    }
    store.preferences.canopy = 95
    await store.calculate('WALK')
    const walking = store.route
    await store.calculate('TRANSIT')
    expect(store.route?.travelMode).toBe('TRANSIT')
    expect(store.route?.match).toBeNull()
    expect(store.route?.metrics).toBeNull()
    await store.calculate('WALK')
    expect(store.route).toEqual(walking)
    store.preferences.canopy = 20
    expect(store.route).toBeNull()
    await store.calculate('WALK')
    expect(store.route?.match?.score).not.toEqual(walking?.match?.score)
  })
  it('does not allow a stale walking request to replace the latest mode', async () => {
    const store = useJourneyStore()
    store.startLocation = {
      id: 'start',
      label: 'Start',
      coordinates: mockPrecincts[1]!.referencePoint,
    }
    store.destination = {
      id: 'end',
      label: 'End',
      coordinates: mockAreas(mockPrecincts[1]!)[0]!.center,
    }
    await Promise.all([store.calculate('WALK'), store.calculate('TRANSIT')])
    expect(store.route?.travelMode).toBe('TRANSIT')
  })
})

describe('session and preferences', () => {
  it('skip clears only environmental preferences and persists resolved location', () => {
    const store = useJourneyStore()
    store.preferences = { canopy: 80, shade: 75, noise: 'quiet', allergy: 'lower', walkingTime: 15 }
    store.startLocation = {
      id: 'k',
      label: 'Kensington',
      coordinates: mockPrecincts[1]!.referencePoint,
    }
    store.skipPersonalisation()
    expect(store.preferences).toEqual({ ...emptyPreferences(), walkingTime: 15 })
    setActivePinia(createPinia())
    expect(useJourneyStore().startLocation?.label).toBe('Kensington')
    expect(useJourneyStore().preferences.walkingTime).toBe(15)
  })
  it('rejects incorrect access, restores a session, and re-locks when storage is cleared', async () => {
    await expect(verifyAccess('wrong')).rejects.toThrow('isn’t right')
    expect(getAccessToken()).toBeNull()
    await verifyAccess(DEMO_PASSWORD)
    expect(getAccessToken()).toMatch(/^demo-/)
    sessionStorage.clear()
    expect(getAccessToken()).toBeNull()
  })
})
