/**
 * Leaf points and visit log rules (Epic 8). Pure functions over a plain state
 * object. The rewards store persists the state on this device only; this file
 * never touches storage or the network.
 */
import type { Mood } from '@/data/sproutMessages'

export const POINTS_PER_WALK = 5
export const CANOPY_FRIEND_VISITS = 3
export const CANOPY_FRIEND_DAYS = 7

export interface Visit {
  zoneId: string
  /** Area name at the time of the visit, shown on the badges. */
  label?: string
  /** Local calendar day, YYYY-MM-DD, used for the once-per-area-per-day rule. */
  date: string
  /** ISO timestamp of the visit. */
  at: string
  before: Mood | null
  /** Null when the end-of-walk feeling check-in was skipped. */
  after: Mood | null
}

export interface RewardsState {
  points: number
  visits: Visit[]
}

export const EMPTY_REWARDS: RewardsState = { points: 0, visits: [] }

export function dayKey(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function visitedToday(state: RewardsState, zoneId: string, now: Date): boolean {
  const today = dayKey(now)
  return state.visits.some((visit) => visit.zoneId === zoneId && visit.date === today)
}

/**
 * US8.1 + US8.3: log a finished walk. A second walk to the same area on the same
 * day earns nothing and is not logged again.
 */
export function recordVisit(
  state: RewardsState,
  input: { zoneId: string; label?: string; before: Mood | null; after: Mood | null; now: Date },
): { state: RewardsState; awarded: number; duplicate: boolean } {
  if (visitedToday(state, input.zoneId, input.now)) {
    return { state, awarded: 0, duplicate: true }
  }
  const visit: Visit = {
    zoneId: input.zoneId,
    label: input.label,
    date: dayKey(input.now),
    at: input.now.toISOString(),
    before: input.before,
    after: input.after,
  }
  return {
    state: { ...state, points: state.points + POINTS_PER_WALK, visits: [...state.visits, visit] },
    awarded: POINTS_PER_WALK,
    duplicate: false,
  }
}

/** US8.3: which visit this is for the area, counting the one being logged. */
export function visitNumber(state: RewardsState, zoneId: string): number {
  return state.visits.filter((visit) => visit.zoneId === zoneId).length + 1
}

/** US8.3: Canopy Friend = three visits to the same area within seven days. */
export function canopyFriendProgress(
  state: RewardsState,
  zoneId: string,
  now: Date,
): { visitsInWindow: number; visitsNeeded: number; earned: boolean } {
  const windowStart = now.getTime() - CANOPY_FRIEND_DAYS * 24 * 60 * 60 * 1000
  const dates = new Set(
    state.visits
      .filter((visit) => visit.zoneId === zoneId && new Date(visit.at).getTime() >= windowStart)
      .map((visit) => visit.date),
  )
  const visitsInWindow = dates.size
  return {
    visitsInWindow,
    visitsNeeded: Math.max(0, CANOPY_FRIEND_VISITS - visitsInWindow),
    earned: visitsInWindow >= CANOPY_FRIEND_VISITS,
  }
}
