<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import OnboardingSplash from '@/components/onboarding/OnboardingSplash.vue'
import OnboardingQuestion from '@/components/onboarding/OnboardingQuestion.vue'
import OnboardingChoice from '@/components/onboarding/OnboardingChoice.vue'
import LocationStep from '@/components/onboarding/LocationStep.vue'
import { useDiscoveryStore } from '@/stores/discovery'
import { useOnboardingStore } from '@/stores/onboarding'
import type { Coordinates } from '@/types/discovery'

const router = useRouter()
const discovery = useDiscoveryStore()
const onboarding = useOnboardingStore()
const { step, timeBudget, noiseTolerance, hasAllergies } = storeToRefs(onboarding)
const { loadError } = storeToRefs(discovery)

onMounted(() => discovery.initialize())

// Q1: how much time the person has right now — this becomes the walk-time
// budget used to filter candidate zones once matching is wired up.
const timeOptions = [
  { value: '5', label: '5 minutes', hint: 'Something on the way past' },
  { value: '15', label: '15 minutes', hint: 'A proper break between things' },
  { value: '30+', label: '30+ minutes', hint: "I've got a while" },
]

// Q3: allergy sensitivity — kept as a plain yes/no here; matching against the
// species dataset for high-pollen genera happens where zones get ranked.
const allergyOptions = [
  { value: 'no', label: 'No allergies', hint: 'Any zone works' },
  { value: 'yes', label: 'Yes, I get hay fever', hint: 'Avoid high-pollen trees' },
]

const allergyValue = computed<string | null>({
  get: () => (hasAllergies.value === null ? null : hasAllergies.value ? 'yes' : 'no'),
  set: (value) => {
    hasAllergies.value = value === 'yes'
  },
})

// Q4: starting location — replaces the fixed Melbourne CBD default with
// either the browser's geolocation or a geocoded address, then centres the
// map there once the zones for the nearest precinct are loaded.
async function finishOnboarding(coordinates: Coordinates, label: string, method: 'current' | 'search') {
  onboarding.setLocation(coordinates, label, method)
  await discovery.focusOnLocation(coordinates, label)
  router.push('/map')
}
</script>

<template>
  <main class="onboarding-flow">
    <OnboardingSplash
      v-if="step === 'splash'"
      @personalise="onboarding.startPersonalised()"
      @skip="onboarding.skipToMap()"
    />

    <OnboardingChoice
      v-else-if="step === 'time'"
      v-model="timeBudget"
      title="Let us get to know you"
      question="How much time do you have?"
      :options="timeOptions"
      @back="onboarding.back()"
      @next="onboarding.next()"
    />

    <OnboardingQuestion
      v-else-if="step === 'noise'"
      v-model="noiseTolerance"
      title="Let us get to know you"
      question="Are you ok with noise?"
      left-label="prefer quiet"
      right-label="not fussed"
      @back="onboarding.back()"
      @next="onboarding.next()"
    />

    <OnboardingChoice
      v-else-if="step === 'allergies'"
      v-model="allergyValue"
      title="Let us get to know you"
      question="Any allergies we should route around?"
      :options="allergyOptions"
      @back="onboarding.back()"
      @next="onboarding.next()"
    />

    <template v-else-if="step === 'location'">
      <div v-if="loadError" class="error-banner">
        <ElAlert :title="loadError" type="error" show-icon :closable="false" />
      </div>
      <LocationStep @located="finishOnboarding" @back="onboarding.back()" />
    </template>
  </main>
</template>

<style scoped>
.onboarding-flow {
  min-height: 100vh;
}

.error-banner {
  display: grid;
  gap: 10px;
  width: min(560px, calc(100% - 48px));
  margin: 24px auto 0;
}
</style>
