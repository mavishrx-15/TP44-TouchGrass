import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import type { Mood } from '@/data/sproutMessages'
import {
  recordVisit,
  restoreRewards,
  unlockSkin,
  type RewardsState,
} from '@/services/rewards.logic'
import { getSkin, SPROUT_SKINS, type SkinId } from '@/data/sproutSkins'

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
    return restoreRewards(raw ? JSON.parse(raw) : null)
  } catch {
    return restoreRewards(null)
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

  watch(state, save, { deep: true, flush: 'sync' })
  const ownedSkins = computed(() => state.value.ownedSkins ?? ['classic'])
  const equippedSkin = computed(() => state.value.equippedSkin ?? 'classic')
  const wearing = computed(() => getSkin(equippedSkin.value))
  const hasLockedSkins = computed(() =>
    SPROUT_SKINS.some((skin) => !ownedSkins.value.includes(skin.id)),
  )

  function unlock(id: SkinId) {
    const result = unlockSkin(state.value, id)
    state.value = result.state
    return result.unlocked
  }

  function wear(id: SkinId) {
    if (ownedSkins.value.includes(id)) state.value.equippedSkin = id
  }

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

  return { state, logVisit, ownedSkins, equippedSkin, wearing, hasLockedSkins, unlock, wear }
})
