<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import OnboardingSplash from '@/components/onboarding/OnboardingSplash.vue'
import OnboardingQuestion from '@/components/onboarding/OnboardingQuestion.vue'
import MinimalSearch from '@/components/onboarding/MinimalSearch.vue'
import { useDiscoveryStore } from '@/stores/discovery'
import { useOnboardingStore } from '@/stores/onboarding'

const router = useRouter()
const discovery = useDiscoveryStore()
const onboarding = useOnboardingStore()
const { step, mood, noiseTolerance } = storeToRefs(onboarding)
const { searchError, loadError } = storeToRefs(discovery)

onMounted(() => discovery.initialize())

async function exploreArea(precinctName: string) {
  if (!(await discovery.search(precinctName))) return
  router.push('/map')
}
</script>

<template>
  <AppHeader v-if="step === 'search'" />
  <main class="onboarding-flow">
    <OnboardingSplash v-if="step === 'splash'" @continue="onboarding.next()" />

    <OnboardingQuestion
      v-else-if="step === 'mood'"
      v-model="mood"
      title="Let us get to know you"
      question="How are you feeling today?"
      left-label="calm"
      right-label="stressed"
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

    <template v-else>
      <div v-if="searchError || loadError" class="error-banner">
        <ElAlert
          v-if="searchError"
          :title="searchError"
          type="warning"
          show-icon
          :closable="false"
        />
        <ElAlert v-if="loadError" :title="loadError" type="error" show-icon :closable="false" />
      </div>
      <MinimalSearch
        :initial-value="discovery.selectedPrecinct.name"
        :precincts="discovery.precincts.map((precinct) => precinct.name)"
        @explore="exploreArea"
        @back="onboarding.back()"
      />
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
