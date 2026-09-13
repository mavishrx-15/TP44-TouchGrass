<script setup lang="ts">
import { computed } from 'vue'
import LocationSearch from '@/components/LocationSearch.vue'
import PersonalisedRouteCard from '@/components/PersonalisedRouteCard.vue'
import { useJourneyStore } from '@/stores/journey'
import type { RouteEndpoint, RouteOption, RoutePlace, TreeZone } from '@/types/discovery'
withDefaults(
  defineProps<{
    options?: RouteOption[]
    zones?: TreeZone[]
    loading?: boolean
    error?: string | null
    collapsed?: boolean
  }>(),
  { options: () => [], zones: () => [], collapsed: false },
)
const emit = defineEmits<{
  route: [origin: RouteEndpoint, destination: RouteEndpoint]
  close: []
  'toggle-collapse': []
}>()
const journey = useJourneyStore()
void journey.initialize()
const origin = computed<RoutePlace | null>({
  get: () =>
    journey.startLocation
      ? { id: 'origin', label: journey.startLocationLabel, coordinates: journey.startLocation }
      : null,
  set: journey.setStart,
})
function calculate() {
  if (origin.value && journey.destination) emit('route', origin.value, journey.destination)
}
</script>
<template>
  <section class="route-planner" aria-label="Route planner">
    <header>
      <strong>Directions</strong
      ><ElButton text @click="emit('toggle-collapse')">{{
        collapsed ? 'Expand' : 'Collapse'
      }}</ElButton
      ><ElButton text aria-label="Close directions" @click="emit('close')">Close</ElButton>
    </header>
    <div v-if="!collapsed" class="planner-content">
      <LocationSearch
        v-model="origin"
        label="Starting location"
        :precincts="journey.precincts"
        allow-geolocation
      />
      <LocationSearch
        v-model="journey.destination"
        label="Destination"
        :precincts="journey.precincts"
      />
      <ElSelect
        v-if="zones.length"
        placeholder="Or choose a tree area"
        aria-label="Choose tree area"
        @change="
          (id: string) => {
            const zone = zones.find((z) => z.id === id)
            if (zone)
              journey.destination = { id: zone.id, label: zone.label, coordinates: zone.center }
          }
        "
        ><ElOption v-for="zone in zones" :key="zone.id" :value="zone.id" :label="zone.label"
      /></ElSelect>
      <ElButton
        type="primary"
        :loading="loading"
        :disabled="!origin || !journey.destination || !journey.allergyValid"
        @click="calculate"
        >Calculate route</ElButton
      >
      <ElAlert v-if="error" :title="error" type="error" :closable="false" />
      <PersonalisedRouteCard v-if="options[0]" :route="options[0]" />
      <RouterLink to="/personalised-route" class="text-action"
        >Open personalised route and transport options</RouterLink
      >
    </div>
  </section>
</template>
<style scoped>
.route-planner {
  position: absolute;
  z-index: 12;
  top: 22px;
  left: 50%;
  transform: translateX(-50%);
  width: min(520px, calc(100% - 48px));
  max-height: calc(100% - 70px);
  overflow: auto;
  border: 1px solid var(--tg-border);
  border-radius: 18px;
  background: white;
  box-shadow: 0 14px 38px rgb(31 68 35 / 20%);
}
header {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid var(--tg-border);
}
header strong {
  margin-right: auto;
}
.planner-content {
  padding: 20px;
  display: grid;
  gap: 18px;
}
</style>
