import { apiGet } from '@/api/client'
import type { Coordinates, DensityTier, MapBounds, TreeGenus, TreeZone } from '@/types/discovery'

/**
 * Melbourne CBD boundary and zones, read from the backend's single source of
 * truth (`backend/app/cbd.py`, owner Tian): `GET /api/cbd/zones`. The real
 * outline is the actual Hoddle Grid polygon (198 zones), not a bounding
 * rectangle - a straight box used to draw in parts of Yarra Park, Jolimont
 * and the Botanic Gardens fringe that aren't really "the CBD".
 */

interface CbdApiZone {
  id: string
  precinctId: string
  precinctName: string
  label: string
  center: Coordinates
  bounds: MapBounds
  treeCount: number
  density: DensityTier
  dominantGenus: TreeGenus | null
  distanceKm: number
  nearestStreet: string | null
}

interface CbdZonesApiResponse {
  boundary: { type: 'Polygon'; coordinates: [number, number][][] } // rings of [lng, lat]
  bounds: MapBounds
  zoneCount: number
  densityCounts: Record<DensityTier, number>
  zones: CbdApiZone[]
}

export interface CbdData {
  /** CBD tree zones, already adapted to the shape every map component expects. */
  zones: TreeZone[]
  /** The real Hoddle Grid outline, ready for the map's dashed boundary line. */
  outline: Coordinates[]
  zoneCount: number
  densityCounts: Record<DensityTier, number>
  bounds: MapBounds
}

// Used only until the real polygon has loaded once, early in a session.
const FALLBACK_BOUNDS: MapBounds = { south: -37.823, north: -37.8048, west: 144.9528, east: 144.9722 }
export const CBD_CENTER: Coordinates = {
  lat: (FALLBACK_BOUNDS.south + FALLBACK_BOUNDS.north) / 2,
  lng: (FALLBACK_BOUNDS.west + FALLBACK_BOUNDS.east) / 2,
}

/** The `/api/precincts` entry for the CBD - unrelated to the zones endpoint above. */
export const CBD_PRECINCT_ID = 'melbourne'

let loadPromise: Promise<CbdData> | null = null
/** The raw [lng, lat] ring, kept for isWithinCbd's point-in-polygon test. */
let ring: [number, number][] | null = null

function adaptZone(zone: CbdApiZone): TreeZone {
  return {
    id: zone.id,
    precinctId: zone.precinctId,
    label: zone.label,
    nearestStreet: zone.nearestStreet,
    center: zone.center,
    bounds: zone.bounds,
    treeCount: zone.treeCount,
    density: zone.density,
    dominantGenus: zone.dominantGenus,
    distanceKm: zone.distanceKm,
    description: `${zone.density}-density tree cluster${zone.dominantGenus ? ` dominated by ${zone.dominantGenus}` : ''}.`,
    mapPosition: { x: 0, y: 0, width: 0, height: 0 },
  }
}

/**
 * Fetches the CBD zones and boundary once per session and caches the result;
 * every caller (Sprout's map step, the live walk) gets the same promise.
 */
export function loadCbdZones(signal?: AbortSignal): Promise<CbdData> {
  if (!loadPromise) {
    loadPromise = apiGet<CbdZonesApiResponse>('/api/cbd/zones', signal)
      .then((data) => {
        ring = data.boundary.coordinates[0] ?? null
        return {
          zones: data.zones.map(adaptZone),
          outline: ring ? ring.map(([lng, lat]) => ({ lat, lng })) : [],
          zoneCount: data.zoneCount,
          densityCounts: data.densityCounts,
          bounds: data.bounds,
        }
      })
      .catch((error) => {
        loadPromise = null
        throw error
      })
  }
  return loadPromise
}

export interface ZoneFacts {
  zoneId: string
  treeCount: number
  density: DensityTier
  topSpecies: { commonName: string; count: number }[]
}

/** US6.3's "almost there" tip: the destination zone's real tree count and top species. */
export function getZoneFacts(zoneId: string, signal?: AbortSignal): Promise<ZoneFacts> {
  return apiGet<ZoneFacts>(`/api/zones/${encodeURIComponent(zoneId)}/facts`, signal)
}

/**
 * Whether a point is inside the real CBD polygon. Before the first
 * `loadCbdZones()` resolves, this falls back to a rough bounding box rather
 * than refusing every check - the gap is a second or two at most, since
 * every caller already triggers a load on mount.
 */
export function isWithinCbd(point: Coordinates): boolean {
  if (ring) return pointInRing(point, ring)
  return (
    point.lat >= FALLBACK_BOUNDS.south &&
    point.lat <= FALLBACK_BOUNDS.north &&
    point.lng >= FALLBACK_BOUNDS.west &&
    point.lng <= FALLBACK_BOUNDS.east
  )
}

// Ray casting, mirroring backend/app/cbd.py's contains() so both sides agree.
function pointInRing(point: Coordinates, polygon: [number, number][]): boolean {
  let inside = false
  for (let i = 0; i < polygon.length - 1; i++) {
    const [ax, ay] = polygon[i]!
    const [bx, by] = polygon[i + 1]!
    if (ay > point.lat !== by > point.lat && point.lng < ax + ((point.lat - ay) * (bx - ax)) / (by - ay)) {
      inside = !inside
    }
  }
  return inside
}
