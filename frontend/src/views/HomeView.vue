<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import LocationSearch from '@/components/LocationSearch.vue'
import PreferenceControls from '@/components/PreferenceControls.vue'
import { useJourneyStore } from '@/stores/journey'
import { COVERAGE_RADIUS_KM } from '@/services/preferences'
import type { RoutePlace } from '@/types/discovery'
const journey = useJourneyStore()
const router = useRouter()
const origin = computed<RoutePlace | null>({
  get: () =>
    journey.startLocation
      ? { id: 'origin', label: journey.startLocationLabel, coordinates: journey.startLocation }
      : null,
  set: journey.setStart,
})
onMounted(() => journey.initialize())
</script>
<template>
  <AppHeader />
  <main class="page-container journey-page">
    <header class="journey-intro">
      <span class="eyebrow">A little greener. A little more you.</span>
      <h1>Find your way to greener places.</h1>
      <p>
        Choose where you start and what matters to you. We’ll find an area to explore and a route
        that fits.
      </p>
    </header>
    <div class="home-layout">
      <section class="journey-panel">
        <h2>1. Where are you starting?</h2>
        <LocationSearch
          v-model="origin"
          label="Starting location"
          :precincts="journey.precincts"
          allow-geolocation
        />
        <p v-if="journey.loading" role="status">Loading supported precincts…</p>
        <div v-if="journey.error" role="alert">
          <p class="form-error">{{ journey.error }}</p>
          <ElButton @click="journey.initialize">Retry</ElButton>
        </div>
        <ElAlert
          v-if="origin && !journey.covered && !journey.loading && !journey.error"
          title="Outside our current coverage"
          :description="`Choose a location within ${COVERAGE_RADIUS_KM} km of a listed Melbourne precinct centre.`"
          type="warning"
          :closable="false"
        />
        <p v-if="journey.covered" class="success-note">
          Tree data near {{ journey.originPrecinct?.name }} is available.
        </p>
      </section>
      <section class="journey-panel">
        <h2>2. Make it your walk</h2>
        <p class="muted">Set each priority from 0 (no preference) to 5 (most important).</p>
        <PreferenceControls />
      </section>
    </div>
    <section class="journey-actions">
      <ElButton
        type="primary"
        size="large"
        :disabled="!journey.ready || journey.loading"
        @click="router.push('/recommendations')"
        >Explore recommendations</ElButton
      ><ElButton
        size="large"
        :disabled="!journey.ready || journey.loading"
        @click="router.push('/personalised-route')"
        >Route to a destination</ElButton
      >
      <p v-if="!origin">Confirm your starting location to continue.</p>
    </section>
  </main>
</template>
