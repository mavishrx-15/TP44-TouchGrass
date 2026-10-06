import { describe, expect, it } from 'vitest'
import {
  OFF_ROUTE_M,
  distanceM,
  findTurns,
  minutesLeft,
  nextOffRouteState,
  pointAtDistance,
  pickTip,
  progressAlong,
  zoneContaining,
  type TipCandidate,
} from '@/services/walk'

// A straight east-west route. At this latitude 0.001 degrees of longitude is about 88 metres.
const route = [
  { lat: -37.8, lng: 144.96 },
  { lat: -37.8, lng: 144.961 },
  { lat: -37.8, lng: 144.962 },
]

describe('progressAlong (US6.2)', () => {
  it('reports walked and remaining distance from a fix on the route', () => {
    const halfway = { lat: -37.8, lng: 144.961 } // the middle vertex, exactly half way
    const progress = progressAlong(route, halfway)
    expect(progress.totalM).toBeGreaterThan(150)
    expect(progress.walkedM).toBeCloseTo(progress.totalM / 2, 0)
    expect(progress.offRouteM).toBeLessThan(1)
  })

  it('measures how far a fix sits off the route', () => {
    const offset = { lat: -37.8 + 0.0003, lng: 144.9605 } // about 33 m north
    const progress = progressAlong(route, offset)
    expect(progress.offRouteM).toBeGreaterThan(30)
    expect(progress.offRouteM).toBeLessThan(40)
  })

  it('clamps a fix past the end to the destination', () => {
    const past = progressAlong(route, { lat: -37.8, lng: 144.99 })
    expect(past.remainingM).toBe(0)
    expect(past.walkedM).toBeCloseTo(past.totalM, 0)
  })
})

describe('pace and off-route rules', () => {
  it('uses 80 metres per minute for time left (US6.2)', () => {
    expect(minutesLeft(800)).toBe(10)
    expect(minutesLeft(801)).toBe(11)
    expect(minutesLeft(0)).toBe(0)
  })

  it('asks about a reroute only after 20 seconds continuously over 40 metres', () => {
    let state = { offSince: null, shouldAsk: false }
    state = nextOffRouteState(state, OFF_ROUTE_M + 5, 0)
    expect(state.shouldAsk).toBe(false)
    state = nextOffRouteState(state, OFF_ROUTE_M + 5, 20_000)
    expect(state.shouldAsk).toBe(false)
    state = nextOffRouteState(state, OFF_ROUTE_M + 5, 20_001)
    expect(state.shouldAsk).toBe(true)
  })

  it('resets the timer when the user is back on the route', () => {
    let state = nextOffRouteState({ offSince: null, shouldAsk: false }, 80, 0)
    state = nextOffRouteState(state, 10, 5_000)
    expect(state).toEqual({ offSince: null, shouldAsk: false })
  })
})

describe('tips (US6.3)', () => {
  const tip = (key: string): TipCandidate => ({ kind: 'breathe', key, text: key })

  it('waits while a tip was shown less than 60 seconds ago', () => {
    expect(pickTip([tip('a')], new Set(), 1_000, 30_000)).toBeNull()
    expect(pickTip([tip('a')], new Set(), 1_000, 61_000)?.key).toBe('a')
  })

  it('never repeats a tip that was already shown', () => {
    expect(pickTip([tip('a'), tip('b')], new Set(['a']), null, 0)?.key).toBe('b')
    expect(pickTip([tip('a')], new Set(['a']), null, 0)).toBeNull()
  })
})

describe('turns and zones', () => {
  it('finds a sharp corner but not a straight run', () => {
    const corner = [
      { lat: -37.8, lng: 144.96 },
      { lat: -37.8, lng: 144.961 },
      { lat: -37.799, lng: 144.961 },
    ]
    expect(findTurns(route)).toHaveLength(0)
    expect(findTurns(corner)).toHaveLength(1)
  })

  it('finds the zone a position is inside, if any', () => {
    const zones = [{ id: 'z', bounds: { north: -37.79, south: -37.81, east: 144.97, west: 144.95 } }]
    expect(zoneContaining(zones, { lat: -37.8, lng: 144.96 })?.id).toBe('z')
    expect(zoneContaining(zones, { lat: -37.9, lng: 144.96 })).toBeNull()
  })

  it('measures roughly 111 km per degree of latitude', () => {
    expect(distanceM({ lat: 0, lng: 0 }, { lat: 1, lng: 0 })).toBeCloseTo(111_195, -2)
  })
})

describe('pointAtDistance (demo walk)', () => {
  it('places a point part way along the route and clamps at the ends', () => {
    const total = progressAlong(route, route[0]!).totalM
    const middle = pointAtDistance(route, total / 2)
    expect(middle.lng).toBeCloseTo(144.961, 4)
    expect(pointAtDistance(route, -5)).toEqual(route[0])
    expect(pointAtDistance(route, total + 500)).toEqual(route[2])
  })
})
