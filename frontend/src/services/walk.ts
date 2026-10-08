/**
 * Live walk maths (Epic 6). Pure functions only: the walk screen feeds them
 * GPS fixes and reads back progress, off-route state and which tip is due.
 *
 * Everything here runs on the phone. Positions are never sent to the server
 * (Epic 6 quality rule), so nothing in this file imports the API client.
 */
import type { Coordinates } from '@/types/discovery'

export const WALK_PACE_M_PER_MIN = 80
/** Demo walks run this many times faster than the real pace, so a short route plays in under a minute. */
export const DEMO_SPEED = 8
export const OFF_ROUTE_M = 40
export const OFF_ROUTE_SECONDS = 20
export const WEAK_GPS_ACCURACY_M = 50
export const ARRIVAL_RADIUS_M = 40
/**
 * Beyond this, the live position is nowhere near the route - not CBD-specific
 * any more, since a destination can now be anywhere in the city. Used to
 * suggest the demo walk instead of chasing reroute/arrival logic that will
 * never make sense from this far away.
 */
export const FAR_FROM_ROUTE_M = 3000
export const TURN_ALERT_M = 50
export const ALMOST_RADIUS_M = 100
export const TIP_COOLDOWN_MS = 60_000
/** A bend sharper than this counts as a turn worth a DIRECTION tip. */
const TURN_ANGLE_DEG = 30

const EARTH_RADIUS_M = 6_371_000

/** Great-circle distance in metres. */
export function distanceM(a: Coordinates, b: Coordinates): number {
  const rad = (d: number) => (d * Math.PI) / 180
  const dLat = rad(b.lat - a.lat)
  const dLng = rad(b.lng - a.lng)
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)))
}

/** Compass point for the direction of travel from `a` to `b`. */
export function compassFrom(a: Coordinates, b: Coordinates): string {
  const rad = (d: number) => (d * Math.PI) / 180
  const dLng = rad(b.lng - a.lng)
  const y = Math.sin(dLng) * Math.cos(rad(b.lat))
  const x =
    Math.cos(rad(a.lat)) * Math.sin(rad(b.lat)) -
    Math.sin(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.cos(dLng)
  const bearing = (Math.atan2(y, x) * 180) / Math.PI
  const points = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west']
  return points[Math.round((((bearing + 360) % 360) / 45)) % 8]!
}

export interface WalkProgress {
  /** Metres walked along the route, measured from the first point. */
  walkedM: number
  totalM: number
  remainingM: number
  /** Distance from the position to the nearest point on the route. */
  offRouteM: number
  /** Index of the route point just behind the position. */
  segmentIndex: number
  /** The route point the position projects onto, used to split solid and dashed lines. */
  snapped: Coordinates
}

/**
 * Projects a GPS fix onto the route. Uses a flat-earth approximation per
 * segment, which is accurate to well under a metre across a few hundred metres.
 */
export function progressAlong(path: Coordinates[], position: Coordinates): WalkProgress {
  if (path.length === 0) {
    return { walkedM: 0, totalM: 0, remainingM: 0, offRouteM: 0, segmentIndex: 0, snapped: position }
  }
  const cumulative = [0]
  for (let i = 1; i < path.length; i++) {
    cumulative.push(cumulative[i - 1]! + distanceM(path[i - 1]!, path[i]!))
  }
  const totalM = cumulative[cumulative.length - 1]!

  let best = { offRouteM: Infinity, segmentIndex: 0, walkedM: 0, snapped: path[0]! }
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i]!
    const b = path[i + 1]!
    const cosLat = Math.cos((a.lat * Math.PI) / 180)
    // Local metres: x east, y north, origin at segment start.
    const bx = (b.lng - a.lng) * cosLat
    const by = b.lat - a.lat
    const px = (position.lng - a.lng) * cosLat
    const py = position.lat - a.lat
    const lenSq = bx * bx + by * by
    const t = lenSq === 0 ? 0 : Math.min(1, Math.max(0, (px * bx + py * by) / lenSq))
    const snapped = { lat: a.lat + by * t, lng: a.lng + (b.lng - a.lng) * t }
    const offRouteM = distanceM(position, snapped)
    if (offRouteM < best.offRouteM) {
      best = {
        offRouteM,
        segmentIndex: i,
        walkedM: cumulative[i]! + distanceM(a, snapped),
        snapped,
      }
    }
  }
  return {
    walkedM: best.walkedM,
    totalM,
    remainingM: Math.max(0, totalM - best.walkedM),
    offRouteM: best.offRouteM,
    segmentIndex: best.segmentIndex,
    snapped: best.snapped,
  }
}

/** US6.2: minutes left at the fixed 80 metres-per-minute pace. */
export function minutesLeft(remainingM: number): number {
  return Math.max(0, Math.ceil(remainingM / WALK_PACE_M_PER_MIN))
}

export function formatDistance(metres: number): string {
  return metres >= 1000 ? `${(metres / 1000).toFixed(1)} km` : `${Math.round(metres)} m`
}

export interface OffRouteState {
  /** When the user first went off route, or null while they are on it. */
  offSince: number | null
  /** True once they have been off route for more than OFF_ROUTE_SECONDS. */
  shouldAsk: boolean
}

/** US6.2: a reroute question only after 20 seconds continuously over 40 metres away. */
export function nextOffRouteState(
  previous: OffRouteState,
  offRouteM: number,
  now: number,
): OffRouteState {
  if (offRouteM <= OFF_ROUTE_M) return { offSince: null, shouldAsk: false }
  const offSince = previous.offSince ?? now
  return {
    offSince,
    shouldAsk: now - offSince > OFF_ROUTE_SECONDS * 1000,
  }
}

/** A turn on the route: the vertex where the heading changes sharply. */
export interface Turn {
  index: number
  at: Coordinates
  /** Direction of travel after the turn, for the DIRECTION tip. */
  heading: string
}

export function findTurns(path: Coordinates[]): Turn[] {
  const turns: Turn[] = []
  for (let i = 1; i < path.length - 1; i++) {
    const inBearing = bearingDeg(path[i - 1]!, path[i]!)
    const outBearing = bearingDeg(path[i]!, path[i + 1]!)
    let delta = Math.abs(outBearing - inBearing) % 360
    if (delta > 180) delta = 360 - delta
    if (delta >= TURN_ANGLE_DEG) {
      turns.push({ index: i, at: path[i]!, heading: compassFrom(path[i]!, path[i + 1]!) })
    }
  }
  return turns
}

function bearingDeg(a: Coordinates, b: Coordinates): number {
  const rad = (d: number) => (d * Math.PI) / 180
  const dLng = rad(b.lng - a.lng)
  const y = Math.sin(dLng) * Math.cos(rad(b.lat))
  const x =
    Math.cos(rad(a.lat)) * Math.sin(rad(b.lat)) -
    Math.sin(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.cos(dLng)
  return (Math.atan2(y, x) * 180) / Math.PI
}

/** The walk's live-tip kinds, in the priority order they are considered. */
export type TipKind = 'almost' | 'direction' | 'trees' | 'checkin' | 'breathe'

export interface TipCandidate {
  kind: TipKind
  /** Key that makes a tip one-off (e.g. a specific turn), so it is not repeated. */
  key: string
  text: string
}

/**
 * Picks the tip to show now. A tip waits while another was shown less than
 * 60 seconds ago (US6.3), and a key already shown is never repeated.
 */
export function pickTip(
  candidates: TipCandidate[],
  shownKeys: ReadonlySet<string>,
  lastTipAt: number | null,
  now: number,
): TipCandidate | null {
  if (lastTipAt !== null && now - lastTipAt < TIP_COOLDOWN_MS) return null
  return candidates.find((candidate) => !shownKeys.has(candidate.key)) ?? null
}

/** The zone whose bounds contain the position, if any. */
export function zoneContaining<T extends { bounds: { north: number; south: number; east: number; west: number } }>(
  zones: T[],
  position: Coordinates,
): T | null {
  return (
    zones.find(
      (zone) =>
        position.lat <= zone.bounds.north &&
        position.lat >= zone.bounds.south &&
        position.lng <= zone.bounds.east &&
        position.lng >= zone.bounds.west,
    ) ?? null
  )
}

/** The point a given distance along the route, clamped to the ends. Used by the demo walk. */
export function pointAtDistance(path: Coordinates[], metres: number): Coordinates {
  if (path.length === 0) return { lat: 0, lng: 0 }
  let left = Math.max(0, metres)
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i]!
    const b = path[i + 1]!
    const segment = distanceM(a, b)
    if (segment > 0 && left <= segment) {
      const t = left / segment
      return { lat: a.lat + (b.lat - a.lat) * t, lng: a.lng + (b.lng - a.lng) * t }
    }
    left -= segment
  }
  return path[path.length - 1]!
}
