import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { Coordinates } from '@/types/discovery'

export type OnboardingStep = 'splash' | 'time' | 'noise' | 'allergies' | 'location'
export type TimeBudget = '5' | '15' | '30+'
export type LocationMethod = 'current' | 'search'

const STEP_ORDER: OnboardingStep[] = ['splash', 'time', 'noise', 'allergies', 'location']

/**
 * Drives the minimal, one-question-at-a-time entry flow on the home page:
 * splash -> time available -> noise tolerance -> allergies -> starting location.
 * Answers are kept here so the map/recommendation logic can read them without
 * re-plumbing the flow.
 */
export const useOnboardingStore = defineStore('onboarding', () => {
  const step = ref<OnboardingStep>('splash')
  const timeBudget = ref<TimeBudget | null>(null)
  // 1-7 scale, defaulting to the midpoint until the person picks a value.
  const noiseTolerance = ref(4)
  const hasAllergies = ref<boolean | null>(null)
  const locationMethod = ref<LocationMethod | null>(null)
  const startLocation = ref<Coordinates | null>(null)
  const startLocationLabel = ref('')
  // Set from the splash screen's two entry points. null until chosen; false
  // means "just show me the map" skipped the preference questions, so
  // matching logic should treat time/noise/allergies as unanswered rather
  // than as their default values.
  const wantsPersonalisation = ref<boolean | null>(null)

  function next() {
    const index = STEP_ORDER.indexOf(step.value)
    if (index < STEP_ORDER.length - 1) step.value = STEP_ORDER[index + 1]
  }

  function back() {
    // "Just show me the map" jumped straight from splash to location,
    // skipping time/noise/allergies, so stepping back should return to
    // splash rather than resurface a question that was never asked.
    if (wantsPersonalisation.value === false && step.value === 'location') {
      step.value = 'splash'
      return
    }
    const index = STEP_ORDER.indexOf(step.value)
    if (index > 0) step.value = STEP_ORDER[index - 1]
  }

  /** Splash's "Get my spot" button: walk through time / noise / allergies. */
  function startPersonalised() {
    wantsPersonalisation.value = true
    step.value = 'time'
  }

  /** Splash's "Just show me the map" button: location is still required
   * (there's no map without it), everything else is skipped. */
  function skipToMap() {
    wantsPersonalisation.value = false
    step.value = 'location'
  }

  function setLocation(coordinates: Coordinates, label: string, method: LocationMethod) {
    startLocation.value = coordinates
    startLocationLabel.value = label
    locationMethod.value = method
  }

  function reset() {
    step.value = 'splash'
    timeBudget.value = null
    noiseTolerance.value = 4
    hasAllergies.value = null
    locationMethod.value = null
    startLocation.value = null
    startLocationLabel.value = ''
    wantsPersonalisation.value = null
  }

  return {
    step,
    timeBudget,
    noiseTolerance,
    hasAllergies,
    locationMethod,
    startLocation,
    startLocationLabel,
    wantsPersonalisation,
    next,
    back,
    startPersonalised,
    skipToMap,
    setLocation,
    reset,
  }
})
