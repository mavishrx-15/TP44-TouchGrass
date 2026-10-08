<script setup lang="ts">
import { computed, watch } from 'vue'
import { useJourneyStore } from '@/stores/journey'
import { useRewardsStore } from '@/stores/rewards'
import { POINTS_PER_WALK, dayKey } from '@/services/rewards.logic'
import type { AreaOption } from '@/types/planning'

/**
 * US8.4 / Epic 8 "after a walk": three tree-dense areas nearby, from
 * POST /api/sprout/areas - the same ranking "Grow my route" itself uses.
 * Areas already visited today are excluded server-side (the backend keeps no
 * visit history of its own, so the device sends the zone ids to leave out).
 * Layout follows the prototype's numbered list with the points each is worth.
 */
const emit = defineEmits<{ pick: [area: AreaOption] }>()

const journey = useJourneyStore()
const rewards = useRewardsStore()

const candidates = computed(() => journey.sproutAreas)

/** An area with no visit on this device, on any day, is a "new area". */
function isNew(area: AreaOption): boolean {
  return !rewards.state.visits.some((visit) => visit.zoneId === area.destination.zoneId)
}

function loadAreas() {
  if (!journey.startLocation) return
  const today = dayKey(new Date())
  const excludedZoneIds = rewards.state.visits
    .filter((visit) => visit.date === today)
    .map((visit) => visit.zoneId)
  void journey.findSproutAreas({ excludedZoneIds, limit: 3 })
}

watch(
  () => [
    journey.startLocation?.coordinates.lat,
    journey.startLocation?.coordinates.lng,
    rewards.state.visits.length,
  ],
  loadAreas,
  { immediate: true },
)
</script>

<template>
  <section class="nearby">
    <span class="eyebrow">FIND MORE TREES NEAR YOU</span>
    <p v-if="journey.startLocation" class="empty">
      Starting from {{ journey.startLocation.label }}.
    </p>
    <p v-if="!journey.startLocation" class="empty">
      Choose a start point on the Journey map to see nearby areas.
    </p>
    <p v-else-if="journey.sproutAreasLoading" class="empty">Looking for nearby areas…</p>
    <p v-else-if="journey.sproutAreasError" class="empty">{{ journey.sproutAreasError }}</p>
    <p v-else-if="candidates.length === 0" class="empty">
      No other tree-dense areas to suggest right now.
    </p>
    <ol v-else class="list">
      <li v-for="(area, index) in candidates" :key="area.destination.zoneId">
        <button
          type="button"
          class="area"
          :disabled="journey.sproutRouteLoading"
          @click="emit('pick', area)"
        >
          <span class="number" aria-hidden="true">{{ index + 1 }}</span>
          <span class="text">
            <span class="name">{{ area.destination.label }}</span>
            <span class="meta">
              {{ area.destination.treeCount }} trees · {{ Math.round(area.estimatedMinutes) }} min
              walk<template v-if="isNew(area)"> · new area</template>
            </span>
          </span>
          <span class="points">+{{ POINTS_PER_WALK }} pts</span>
        </button>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.nearby {
  display: grid;
  gap: 10px;
  font-family: 'Figtree', system-ui, sans-serif;
  color: #1d2a1d;
}
.eyebrow {
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #1f5a2c;
}
.empty {
  margin: 0;
  color: #6b766a;
  font-size: 0.88rem;
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.area {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  border: 1.5px solid #e0dbcb;
  border-radius: 14px;
  background: white;
  padding: 12px 14px;
  cursor: pointer;
  font-family: inherit;
}
.area:hover {
  border-color: #1f5a2c;
}
.number {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e4eee4;
  color: #1f5a2c;
  font-weight: 700;
  flex-shrink: 0;
}
.text {
  display: grid;
  gap: 2px;
  flex: 1;
  min-width: 0;
}
.name {
  font-weight: 700;
}
.meta {
  font-size: 0.8rem;
  color: #6b766a;
}
.points {
  font-size: 0.78rem;
  font-weight: 800;
  color: #1f5a2c;
  background: #e4eee4;
  border-radius: 999px;
  padding: 4px 10px;
  white-space: nowrap;
}
</style>
