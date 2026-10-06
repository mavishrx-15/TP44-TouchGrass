import { describe, expect, it } from 'vitest'
import { EMPTY_REWARDS, canopyFriendProgress, recordVisit, visitNumber } from '@/services/rewards.logic'

const day = (iso: string) => new Date(iso)

describe('leaf points (US8.1)', () => {
  it('awards 5 points for a finished walk', () => {
    const result = recordVisit(EMPTY_REWARDS, {
      zoneId: 'z1',
      before: null,
      after: 'calm',
      now: day('2026-10-05T10:00:00'),
    })
    expect(result.awarded).toBe(5)
    expect(result.state.points).toBe(5)
  })

  it('gives nothing for a second walk to the same area the same day', () => {
    const first = recordVisit(EMPTY_REWARDS, { zoneId: 'z1', before: null, after: 'calm', now: day('2026-10-05T10:00:00') })
    const second = recordVisit(first.state, { zoneId: 'z1', before: null, after: 'okay', now: day('2026-10-05T15:00:00') })
    expect(second.duplicate).toBe(true)
    expect(second.awarded).toBe(0)
    expect(second.state.visits).toHaveLength(1)
  })

  it('does award a different area on the same day', () => {
    const first = recordVisit(EMPTY_REWARDS, { zoneId: 'z1', before: null, after: 'calm', now: day('2026-10-05T10:00:00') })
    const second = recordVisit(first.state, { zoneId: 'z2', before: null, after: 'calm', now: day('2026-10-05T15:00:00') })
    expect(second.awarded).toBe(5)
  })
})

describe('visits and Canopy Friend (US8.3)', () => {
  it('counts the visit being logged as the next visit number', () => {
    const state = recordVisit(EMPTY_REWARDS, { zoneId: 'z1', before: null, after: 'calm', now: day('2026-10-01T10:00:00') }).state
    expect(visitNumber(state, 'z1')).toBe(2)
    expect(visitNumber(state, 'z2')).toBe(1)
  })

  it('earns Canopy Friend for three visits to one area within seven days', () => {
    let state = EMPTY_REWARDS
    for (const iso of ['2026-10-01T10:00:00', '2026-10-03T10:00:00', '2026-10-05T10:00:00']) {
      state = recordVisit(state, { zoneId: 'z1', before: null, after: 'calm', now: day(iso) }).state
    }
    expect(canopyFriendProgress(state, 'z1', day('2026-10-05T12:00:00')).earned).toBe(true)
  })

  it('does not earn it when the visits are older than seven days', () => {
    let state = EMPTY_REWARDS
    for (const iso of ['2026-09-01T10:00:00', '2026-09-03T10:00:00', '2026-10-05T10:00:00']) {
      state = recordVisit(state, { zoneId: 'z1', before: null, after: 'calm', now: day(iso) }).state
    }
    const progress = canopyFriendProgress(state, 'z1', day('2026-10-05T12:00:00'))
    expect(progress.earned).toBe(false)
    expect(progress.visitsNeeded).toBe(2)
  })
})
