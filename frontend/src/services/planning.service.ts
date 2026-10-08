import { apiPost } from '@/api/client'
import { canopyFromSlider, thermalFromSlider } from '@/data/sproutMessages'
import type { Coordinates } from '@/types/discovery'
import type { Preferences } from '@/types/personalisation'
import type { AreasResponse, PlannedRoute, PlanningPreferences } from '@/types/planning'

/**
 * Sprout's planning calls (`POST /api/sprout/route`, `POST /api/sprout/areas`).
 * The backend picks the destination; preferences are optional and a field the
 * user hasn't set is left out of the request entirely rather than sent as
 * null, since the schema also forbids anything it doesn't list (mood included).
 */

/** Sprout's sliders (0-100) become the backend's named preference values. */
export function buildPlanningPreferences(preferences: Preferences): PlanningPreferences {
  const out: PlanningPreferences = {}
  const canopy = canopyFromSlider(preferences.canopy)
  if (canopy) out.canopy = canopy
  const shade = thermalFromSlider(preferences.shade)
  if (shade) out.shade = shade
  if (preferences.noise) out.noise = preferences.noise
  if (preferences.allergy === 'avoid') out.allergy = 'avoid'
  if (preferences.walkingTime) out.walkingTime = preferences.walkingTime
  return out
}

export function growRoute(
  origin: Coordinates,
  preferences: Preferences,
  signal?: AbortSignal,
  destinationZoneId?: string,
): Promise<PlannedRoute> {
  return apiPost<PlannedRoute>(
    '/api/sprout/route',
    {
      origin,
      preferences: buildPlanningPreferences(preferences),
      ...(destinationZoneId ? { destinationZoneId } : {}),
    },
    signal,
  )
}

export function findAreas(
  origin: Coordinates,
  preferences: Preferences,
  options: { excludedZoneIds?: string[]; limit?: number } = {},
  signal?: AbortSignal,
): Promise<AreasResponse> {
  return apiPost<AreasResponse>(
    '/api/sprout/areas',
    { origin, preferences: buildPlanningPreferences(preferences), ...options },
    signal,
  )
}
