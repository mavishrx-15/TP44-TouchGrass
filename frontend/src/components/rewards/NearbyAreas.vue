<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useJourneyStore } from '@/stores/journey'
import { useRewardsStore } from '@/stores/rewards'
import { POINTS_PER_WALK, visitedToday } from '@/services/rewards.logic'
import type { Recommendation } from '@/types/personalisation'

/**
 * US8.4 / Epic 8 "after a walk": three tree-dense areas nearby, ranked the same
 * way as "See other options" (it reads the same journey recommendations list).
 * Areas already visited today are left out. Layout follows the prototype's
 * numbered list with the points each area is worth.
 */
const emit = defineEmits<{ pick: [area: Recommendation] }>()

const journey = useJourneyStore()
const rewards = useRewardsStore()

const now = new Date()

const candidates = computed<Recommendation[]>(() =>
  journey.recommendations.filter((area) => !visitedToday(rewards.state, area.id, now)).slice(0, 3),
)

/** An area with no visit on this device yet is a "new area". */
function isNew(area: Recommendation): boolean {
  return !rewards.state.visits.some((visit) => visit.zoneId === area.id)
}

onMounted(() => {
  if (journey.startLocation && journey.recommendations.length === 0) {
    void journey.refreshAreas()
  }
})
</script>

<template>
  <section class="nearby">
    <span class="eyebrow">FIND MORE TREES NEAR YOU</span>
    <p v-if="!journey.startLocation" class="empty">Choose a start point on the Journey map to see nearby areas.</p>
    <p v-else-if="journey.areasLoading" class="empty">Looking for nearby areas…</p>
    <p v-else-if="candidates.length === 0" class="empty">No other tree-dense areas to suggest right now.</p>
    <ol v-else class="list">
      <li v-for="(area, index) in candidates" :key="area.id">
        <button type="button" class="area" @click="emit('pick', area)">
          <span class="number" aria-hidden="true">{{ index + 1 }}</span>
          <span class="text">
            <span class="name">{{ area.precinctName }} · {{ area.nearestStreet ?? 'Nearby street' }}</span>
            <span class="meta">
              {{ area.treeCount }} trees · {{ area.estimatedMinutes }} min walk<template v-if="isNew(area)"> · new area</template>
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
