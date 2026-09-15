import { distanceKm } from '@/services/discovery.service'
import type { Coordinates, Precinct, Preferences, TreeZone } from '@/types/discovery'

// Product threshold is configurable until the full AC12 specifies a value.
const configuredRadius = Number(import.meta.env.VITE_COVERAGE_RADIUS_KM || 5)
export const COVERAGE_RADIUS_KM =
  Number.isFinite(configuredRadius) && configuredRadius > 0 ? configuredRadius : 5

export function nearestPrecinct(origin: Coordinates, precincts: Precinct[]) {
  return [...precincts].sort(
    (a, b) => distanceKm(origin, a.referencePoint) - distanceKm(origin, b.referencePoint),
  )[0]
}
export function withinCoverage(
  origin: Coordinates,
  precincts: Precinct[],
  radius = COVERAGE_RADIUS_KM,
) {
  const nearest = nearestPrecinct(origin, precincts)
  return !!nearest && distanceKm(origin, nearest.referencePoint) <= radius
}

export function rankRecommendations(
  zones: TreeZone[],
  origin: Coordinates,
  preferences: Preferences,
) {
  const maximum = Math.max(1, ...zones.map((zone) => zone.treeCount))
  const genera = new Set(preferences.avoidGenera.map((s) => s.trim().toLowerCase()))
  const families = new Set(preferences.avoidFamilies.map((s) => s.trim().toLowerCase()))
  const totalWeight =
    preferences.canopy + preferences.shade + preferences.noise + preferences.allergy
  return zones
    .map((zone) => {
      const total = zone.treeProfile.reduce((n, row) => n + row.count, 0)
      const parks = zone.treeProfile.reduce(
        (n, row) => n + (row.locatedIn === 'Park' ? row.count : 0),
        0,
      )
      const avoided = zone.treeProfile.reduce(
        (n, row) =>
          n +
          (genera.has(row.genus.toLowerCase()) || families.has(row.family.toLowerCase())
            ? row.count
            : 0),
        0,
      )
      const parkShare = total ? parks / total : 0
      const allergyMatch = total ? 1 - avoided / total : 0
      const distance = distanceKm(origin, zone.center)
      const estimatedMinutes = Math.ceil((distance / 4.8) * 60)
      const score = totalWeight
        ? ((zone.treeCount / maximum) * preferences.canopy +
            parkShare * (preferences.shade + preferences.noise) +
            allergyMatch * preferences.allergy) /
          totalWeight
        : 0
      const reasons: string[] = []
      if (preferences.canopy)
        reasons.push(`${zone.treeCount} trees; ${zone.density.toLowerCase()} tree density.`)
      if (preferences.shade || preferences.noise)
        reasons.push(
          total
            ? `${Math.round(parkShare * 100)}% of recorded trees are in parks, a proxy for shade and quieter surroundings.`
            : 'Park data is unavailable for this area.',
        )
      if (preferences.allergy)
        reasons.push(
          total
            ? `${Math.round(allergyMatch * 100)}% of recorded trees are outside your chosen avoidance genera/families.`
            : 'Tree avoidance match is unknown for this area.',
        )
      reasons.push(`${distance.toFixed(1)} km from your selected origin (straight-line distance).`)
      return {
        ...zone,
        distanceKm: distance,
        estimatedMinutes,
        score,
        reasons,
        withinTime: estimatedMinutes <= preferences.walkingMinutes,
      }
    })
    .sort(
      (a, b) =>
        Number(b.withinTime) - Number(a.withinTime) ||
        b.score - a.score ||
        a.distanceKm - b.distanceKm,
    )
}
