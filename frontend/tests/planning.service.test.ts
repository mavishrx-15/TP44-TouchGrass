import { describe, expect, it } from 'vitest'
import { buildPlanningPreferences } from '@/services/planning.service'
import { emptyPreferences } from '@/types/personalisation'

describe('buildPlanningPreferences (Iteration 3 contract)', () => {
  it('omits every preference the user has not set, rather than sending null', () => {
    const body = buildPlanningPreferences(emptyPreferences())
    expect(body).toEqual({})
    expect('canopy' in body).toBe(false)
    expect('mood' in body).toBe(false)
  })

  it('maps the sliders to the named values the backend accepts', () => {
    const body = buildPlanningPreferences({
      canopy: 100,
      shade: 100,
      noise: 'quiet',
      allergy: 'avoid',
      walkingTime: 15,
    })
    expect(body).toEqual({ canopy: 'dense', shade: 'cool', noise: 'quiet', allergy: 'avoid', walkingTime: 15 })
  })

  it('never sends "lower" pollen preference - the backend only accepts "avoid"', () => {
    const body = buildPlanningPreferences({ ...emptyPreferences(), allergy: 'lower' })
    expect('allergy' in body).toBe(false)
  })

  it('never sends a mood field, even if one were smuggled onto the preferences object', () => {
    const withMood = { ...emptyPreferences(), mood: 'stressed' } as Record<string, unknown>
    const body = buildPlanningPreferences(withMood as Parameters<typeof buildPlanningPreferences>[0])
    expect('mood' in body).toBe(false)
  })
})
