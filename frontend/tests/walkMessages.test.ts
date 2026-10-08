import { describe, expect, it } from 'vitest'
import { findDamageWord, friendlyError, moodChangeSummary } from '@/data/walkMessages'

describe('damage words (US7.4)', () => {
  it('finds a listed word as a whole word, case-insensitively', () => {
    expect(findDamageWord('A BROKEN branch')).toBe('broken')
    expect(findDamageWord('the tree looks snapped')).toBe('snapped')
  })

  it('ignores words that only contain a damage word', () => {
    expect(findDamageWord('deadline for the shade')).toBeNull()
    expect(findDamageWord('Thanks for the shade')).toBeNull()
  })
})

describe('mood change (US6.6)', () => {
  it('summarises the change in levels', () => {
    expect(moodChangeSummary('stressed', 'calm').text).toBe('Down 3 levels since your walk started')
    expect(moodChangeSummary('calm', 'tense').text).toBe('Up 2 levels')
    expect(moodChangeSummary('okay', 'okay').text).toBe('About the same as before')
  })
})

describe('friendly errors (plain words only)', () => {
  it('turns a blocked location into a plain instruction', () => {
    const denied = { code: 1, PERMISSION_DENIED: 1, message: 'User denied Geolocation' }
    expect(friendlyError(denied, 'fallback')).toMatch(/Location is blocked/)
  })

  it('turns network failures into a connection message, not "Failed to fetch"', () => {
    expect(friendlyError(new TypeError('Failed to fetch'), 'fallback')).toMatch(
      /couldn’t reach TouchGrass/,
    )
  })

  it('keeps our own plain messages unchanged', () => {
    expect(
      friendlyError(new Error('That photo is too large. Try a closer shot.'), 'fallback'),
    ).toBe('That photo is too large. Try a closer shot.')
  })

  it('falls back when nothing usable was thrown', () => {
    expect(friendlyError(undefined, 'The pin could not be placed.')).toBe(
      'The pin could not be placed.',
    )
  })
})
