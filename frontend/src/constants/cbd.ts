import type { MapBounds } from '@/types/discovery'

/**
 * Melbourne CBD boundary used throughout Sprout (Epic 5, US5.5): the map's
 * dashed outline, the CBD-only zone view, and the precinct Sprout's route
 * step is allowed to search within.
 *
 * The "Melbourne" precinct in the database (456 zones) covers far more than
 * the CBD a user would recognise - it reaches into Yarra Park, Jolimont and
 * the Botanic Gardens fringe. This box is trimmed to the Hoddle Grid itself
 * (Spencer-Spring St, Flinders-La Trobe St, plus a small margin), which
 * keeps 226 real zones. Mirrors backend/app/cbd.py - keep both in sync.
 */
export const CBD_BOUNDS: MapBounds = {
  south: -37.823,
  north: -37.8048,
  west: 144.9528,
  east: 144.9722,
}

export const CBD_CENTER = {
  lat: (CBD_BOUNDS.south + CBD_BOUNDS.north) / 2,
  lng: (CBD_BOUNDS.west + CBD_BOUNDS.east) / 2,
}

/** The precinct id (backend/app/routers/map_data.py's `_slug("Melbourne")`). */
export const CBD_PRECINCT_ID = 'melbourne'

export function isWithinCbd(point: { lat: number; lng: number }): boolean {
  return (
    point.lat >= CBD_BOUNDS.south &&
    point.lat <= CBD_BOUNDS.north &&
    point.lng >= CBD_BOUNDS.west &&
    point.lng <= CBD_BOUNDS.east
  )
}
