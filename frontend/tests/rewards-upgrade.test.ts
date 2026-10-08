// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { restoreRewards, unlockSkin } from '@/services/rewards.logic'
import { useRewardsStore } from '@/stores/rewards'
import { SPROUT_SKINS } from '@/data/sproutSkins'
import { reportDocument, reportFiles } from '@/services/report'

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
})

describe('wardrobe and existing rewards', () => {
  it('keeps spent balances and prevents repeat points after a reload, resetting at local midnight', () => {
    const store = useRewardsStore()
    const input = { zoneId: 'z1', before: null, after: null }
    store.state.points = 15
    expect(store.unlock('autumn')).toBe(true)
    expect(store.logVisit({ ...input, now: new Date(2026, 9, 9, 23, 59) }).awarded).toBe(5)
    setActivePinia(createPinia())
    const restored = useRewardsStore()
    expect(restored.state.points).toBe(5)
    expect(restored.logVisit({ ...input, now: new Date(2026, 9, 9, 23, 59) }).awarded).toBe(0)
    expect(restored.logVisit({ ...input, now: new Date(2026, 9, 10, 0, 0) }).awarded).toBe(5)
    expect(restored.state.points).toBe(10)
    expect(restored.state.visits).toHaveLength(2)
    restored.wear('classic')
    restored.wear('autumn')
    expect(restored.state.points).toBe(10)
  })
  it('recognises when there are no more skins to buy', () => {
    const store = useRewardsStore()
    expect(store.hasLockedSkins).toBe(true)
    store.state.ownedSkins = SPROUT_SKINS.map((skin) => skin.id)
    expect(store.hasLockedSkins).toBe(false)
  })
  it('keeps v1 points and visits when adding Classic ownership', () => {
    const visit = {
      zoneId: 'z1',
      date: '2026-10-05',
      at: '2026-10-05T10:00:00Z',
      before: null,
      after: null,
    }
    expect(restoreRewards({ points: 20, visits: [visit] })).toMatchObject({
      points: 20,
      visits: [visit],
      ownedSkins: ['classic'],
      equippedSkin: 'classic',
    })
  })
  it('does not spend when points are insufficient or the skin is already owned', () => {
    const state = restoreRewards({ points: 10 })
    expect(unlockSkin(state, 'night')).toEqual({ state, unlocked: false })
    expect(unlockSkin(restoreRewards({ points: 20 }), 'classic').unlocked).toBe(false)
  })
  it('charges once, equips the new skin and retains its ownership after more walks', () => {
    const store = useRewardsStore()
    store.state.points = 20
    expect(store.unlock('autumn')).toBe(true)
    expect(store.state.points).toBe(5)
    expect(store.unlock('autumn')).toBe(false)
    store.logVisit({ zoneId: 'z1', before: null, after: 'calm' })
    expect(store.state.points).toBe(10)
    store.wear('night')
    expect(store.equippedSkin).toBe('autumn')
    setActivePinia(createPinia())
    expect(useRewardsStore().equippedSkin).toBe('autumn')
    expect(useRewardsStore().ownedSkins).toEqual(['classic', 'autumn'])
  })
  it('recovers invalid ownership and negative balances without losing a valid save', () => {
    expect(
      restoreRewards({ points: -10, ownedSkins: ['night', 'unknown'], equippedSkin: 'autumn' }),
    ).toMatchObject({ points: 0, ownedSkins: ['classic', 'night'], equippedSkin: 'classic' })
  })
})

describe('report handoff', () => {
  const report = {
    body: 'Broken branch',
    location: '-37.81, 144.96',
    date: '9 Oct 2026',
    photoDataUrl: 'data:image/jpeg;base64,AQID',
  }
  it('includes an actual photo file with the location and description', async () => {
    const files = reportFiles(report)
    expect(files).toHaveLength(2)
    expect(files[0]!.name).toBe('touchgrass-tree-report.txt')
    expect(files[1]!.type).toBe('image/jpeg')
    expect(files[1]!.size).toBe(3)
    expect(reportDocument(report)).toContain('src="data:image/jpeg;base64,AQID"')
    expect(reportDocument(report)).toContain('-37.81, 144.96')
  })
  it('escapes visitor text and rejects active image URLs in downloaded documents', () => {
    const html = reportDocument({
      ...report,
      body: '<script>alert(1)</script>',
      photoDataUrl: 'javascript:alert(1)',
    })
    expect(html).toContain('&lt;script&gt;')
    expect(html).not.toContain('<script>')
    expect(html).not.toContain('javascript:')
  })
})
