import { ref } from 'vue'
import { defineStore } from 'pinia'

export type OnboardingStep = 'splash' | 'mood' | 'noise' | 'search'

const STEP_ORDER: OnboardingStep[] = ['splash', 'mood', 'noise', 'search']

/**
 * Drives the minimal, one-question-at-a-time entry flow on the home page:
 * splash -> mood check -> noise tolerance -> suburb search.
 * Answers are kept here so later work (recommending quieter/greener zones)
 * can read them without re-plumbing the flow.
 */
export const useOnboardingStore = defineStore('onboarding', () => {
  const step = ref<OnboardingStep>('splash')
  // 1-7 scale, defaulting to the midpoint until the person picks a value.
  const mood = ref(4)
  const noiseTolerance = ref(4)

  function next() {
    const index = STEP_ORDER.indexOf(step.value)
    if (index < STEP_ORDER.length - 1) step.value = STEP_ORDER[index + 1]
  }

  function back() {
    const index = STEP_ORDER.indexOf(step.value)
    if (index > 0) step.value = STEP_ORDER[index - 1]
  }

  function reset() {
    step.value = 'splash'
    mood.value = 4
    noiseTolerance.value = 4
  }

  return { step, mood, noiseTolerance, next, back, reset }
})
