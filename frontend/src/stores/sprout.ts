import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useJourneyStore } from '@/stores/journey'
import { moodNeedsCalmPreset, type Mood } from '@/data/sproutMessages'

// Mood never leaves the browser (Epic 5 DoD: "Mood data stays on the user's
// device and is not stored on the server") - it lives in its own
// sessionStorage key, never inside journey.ts's PersonalisedRequest payload.
const GREETED_KEY = 'touchgrass.sprout.greeted.v1'
const MOOD_KEY = 'touchgrass.sprout.mood.v1'

export type SproutStep = 'greeting' | 'feel' | 'canopy' | 'shade' | 'journey' | 'location' | 'route'
const STEP_ORDER: SproutStep[] = ['feel', 'canopy', 'shade', 'journey', 'location', 'route']

function restoreMood(): Mood | null {
  try {
    const value = sessionStorage.getItem(MOOD_KEY)
    return value === 'calm' || value === 'okay' || value === 'tense' || value === 'stressed' || value === 'overwhelmed'
      ? value
      : null
  } catch {
    return null
  }
}

export const useSproutStore = defineStore('sprout', () => {
  const hasGreeted = ref(false)
  try {
    hasGreeted.value = sessionStorage.getItem(GREETED_KEY) === '1'
  } catch {
    /* sessionStorage unavailable - greet every time rather than fail. */
  }
  const mood = ref<Mood | null>(restoreMood())
  const step = ref<SproutStep>(hasGreeted.value ? 'feel' : 'greeting')
  const furthestStepIndex = ref(hasGreeted.value ? 0 : -1)
  const calmPresetApplied = ref(false)

  watch(mood, (value) => {
    try {
      if (value) sessionStorage.setItem(MOOD_KEY, value)
      else sessionStorage.removeItem(MOOD_KEY)
    } catch {
      /* Mood persistence is optional - it still works for this page load. */
    }
  })

  const stepIndex = computed(() => STEP_ORDER.indexOf(step.value))
  const progress = computed(() =>
    STEP_ORDER.map((id, index) => ({
      id,
      reached: index <= furthestStepIndex.value,
      active: step.value === id,
    })),
  )

  function markGreeted() {
    hasGreeted.value = true
    try {
      sessionStorage.setItem(GREETED_KEY, '1')
    } catch {
      /* Session-only flag - a failed write just means greeting again next load. */
    }
  }

  /** US5.1: "Hi Sprout, let's go" - opens Step 1 with the progress bar live. */
  function beginGuided() {
    markGreeted()
    step.value = 'feel'
    furthestStepIndex.value = Math.max(furthestStepIndex.value, 0)
  }

  /** US5.1: "Skip to the map" - Steps 1-4 skipped, no preferences touched. */
  function skipToMap() {
    markGreeted()
    step.value = 'location'
  }

  /** US5.1: "Replay intro" - shows the greeting again; answers are kept. */
  function replayIntro() {
    step.value = 'greeting'
  }

  function pickMood(value: Mood) {
    mood.value = value
    if (moodNeedsCalmPreset(value)) applyCalmPreset()
  }

  /**
   * US5.2: picking Stressed or Overwhelmed preselects Deep canopy, Cool and
   * shaded, and Quieter - but only for fields the user hasn't already set,
   * and only the first time this mood is picked, so a later manual change
   * is never silently overwritten.
   */
  function applyCalmPreset() {
    if (calmPresetApplied.value) return
    calmPresetApplied.value = true
    const journey = useJourneyStore()
    if (journey.preferences.canopy === null) journey.preferences.canopy = 100
    if (journey.preferences.shade === null) journey.preferences.shade = 100
    if (journey.preferences.noise === null) journey.preferences.noise = 'quiet'
  }

  function goToStep(target: SproutStep) {
    const targetIndex = STEP_ORDER.indexOf(target)
    if (targetIndex < 0 || targetIndex > furthestStepIndex.value) return
    step.value = target
  }

  function next() {
    const nextIndex = stepIndex.value + 1
    if (nextIndex >= STEP_ORDER.length) return
    step.value = STEP_ORDER[nextIndex]!
    furthestStepIndex.value = Math.max(furthestStepIndex.value, nextIndex)
  }

  function back() {
    const prevIndex = stepIndex.value - 1
    if (prevIndex < 0) return
    step.value = STEP_ORDER[prevIndex]!
  }

  return {
    hasGreeted,
    mood,
    step,
    progress,
    calmPresetApplied,
    beginGuided,
    skipToMap,
    replayIntro,
    pickMood,
    goToStep,
    next,
    back,
  }
})
