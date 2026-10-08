import { getPrecinctZones, getPrecincts } from '@/services/discovery.service'
import { apiGet } from '@/api/client'
import type { Coordinates, DensityTier, TreeZone } from '@/types/discovery'

/**
 * Tree-dense zones across every precinct, not a CBD-only subset. Sprout and
 * the live walk used to be scoped to the Hoddle Grid CBD polygon
 * (GET /api/cbd/zones); that restriction was dropped by team decision, so
 * this loads the same citywide data the original Explore map used
 * (GET /api/precincts + GET /api/zones?precinct=), merged into one list.
 */

export const MELBOURNE_CENTER: Coordinates = { lat: -37.8136, lng: 144.9631 }

export interface AllZonesData {
  zones: TreeZone[]
  zoneCount: number
}

let loadPromise: Promise<AllZonesData> | null = null

/**
 * Fetches every precinct's zones once per session and caches the result;
 * every caller (Sprout's map step, the live walk) gets the same promise.
 */
export function loadAllZones(signal?: AbortSignal): Promise<AllZonesData> {
  if (!loadPromise) {
    loadPromise = getPrecincts(signal)
      .then((precincts) => Promise.all(precincts.map((p) => getPrecinctZones(p.id, 500, signal))))
      .then((perPrecinct) => {
        const zones = perPrecinct.flat()
        return { zones, zoneCount: zones.length }
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
