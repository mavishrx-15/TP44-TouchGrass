import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import type { Mood } from '@/data/sproutMessages'
import { EMPTY_REWARDS, recordVisit, type RewardsState } from '@/services/rewards.logic'

/**
 * Leaf points and visits (Epic 8). Saved in localStorage so it survives a reload
 * on this device. It is never sent to the server. Storage can be blocked
 * (private windows), so every access is guarded and the app still works for
 * the session if it is.
 */
const STORAGE_KEY = 'touchgrass.rewards.v1'

function load(): RewardsState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...EMPTY_REWARDS, visits: [] }
    const parsed = JSON.parse(raw) as Partial<RewardsState>
    return {
      points: Number.isFinite(parsed.points) ? Number(parsed.points) : 0,
      visits: Array.isArray(parsed.visits) ? parsed.visits : [],
    }
  } catch {
    return { ...EMPTY_REWARDS, visits: [] }
  }
}

function save(state: RewardsState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Storage unavailable: the rewards still work for this session.
  }
}

export const useRewardsStore = defineStore('rewards', () => {
  const state = ref<RewardsState>(load())

  watch(state, save, { deep: true })

  function logVisit(input: {
    zoneId: string
    label?: string
    before: Mood | null
    after: Mood | null
    now?: Date
  }) {
    const result = recordVisit(state.value, { now: new Date(), ...input })
    state.value = result.state
    return result
  }

  return { state, logVisit }
})
