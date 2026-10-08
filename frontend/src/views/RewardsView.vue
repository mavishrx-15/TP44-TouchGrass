<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import NearbyAreas from '@/components/rewards/NearbyAreas.vue'
import { useJourneyStore } from '@/stores/journey'
import { useRewardsStore } from '@/stores/rewards'
import { CANOPY_FRIEND_DAYS, POINTS_PER_WALK, canopyFriendProgress, type Visit } from '@/services/rewards.logic'
import type { AreaOption } from '@/types/planning'
import { ref } from 'vue'

/**
 * Epic 8 Rewards: leaf points, visit badges and nearby areas. Everything is
 * saved on this device only, and the footer says so (US8.1).
 */
const router = useRouter()
const journey = useJourneyStore()
const rewards = useRewardsStore()

const picked = ref<AreaOption | null>(null)

/** One card per visited area, grouped by area id. */
const badges = computed(() => {
  const byArea = new Map<string, Visit[]>()
  for (const visit of rewards.state.visits) {
    byArea.set(visit.zoneId, [...(byArea.get(visit.zoneId) ?? []), visit])
  }
  const now = new Date()
  return [...byArea.entries()].map(([zoneId, visits]) => {
    const latest = visits[visits.length - 1]!
    return {
      zoneId,
      label: latest.label ?? 'A tree-dense area',
      visits: visits.length,
      friend: canopyFriendProgress(rewards.state, zoneId, now),
      first: visits.length === 1,
    }
  })
})

async function choose(area: AreaOption) {
  picked.value = area
  journey.destination = {
    id: area.destination.zoneId,
    label: area.destination.label,
    coordinates: area.destination.center,
  }
  // An explicit pick needs an explicit destination, which only /api/routes takes.
  journey.sproutRoute = null
  await journey.calculate('WALK')
}

function startWalk() {
  router.push('/walk')
}
</script>

<template>
  <main class="rewards-page">
    <section class="card summary">
      <span class="eyebrow">LEAF POINTS</span>
      <h1>{{ rewards.state.points }}</h1>
      <p class="muted">
        You earn {{ POINTS_PER_WALK }} leaf points for each walk you finish. One walk per area per day counts.
      </p>
    </section>

    <section class="card">
      <span class="eyebrow">VISITS AND BADGES</span>
      <p v-if="badges.length === 0" class="muted">
        Finish a walk and your visits will show up here, with a Canopy Friend badge after three in a week.
      </p>
      <ul v-else class="badges">
        <li v-for="badge in badges" :key="badge.zoneId">
          <strong>{{ badge.label }}</strong>
          <span class="muted"> · {{ badge.visits }} visit{{ badge.visits === 1 ? '' : 's' }}</span>
          <p v-if="badge.friend.earned" class="friend">Canopy Friend</p>
          <p v-else-if="badge.first" class="muted">
            You helped care for this area. Visit {{ badge.friend.visitsNeeded }} more times this week to become a Canopy Friend.
          </p>
          <p v-else class="muted">
            Visit {{ badge.friend.visitsNeeded }} more time{{ badge.friend.visitsNeeded === 1 ? '' : 's' }} within {{ CANOPY_FRIEND_DAYS }} days to become a Canopy Friend.
          </p>
        </li>
      </ul>
    </section>

    <section class="card">
      <NearbyAreas @pick="choose" />
    </section>

    <section v-if="picked && journey.route" class="card route" aria-label="Picked route">
      <span class="eyebrow">PERSONALISED WALKING ROUTE</span>
      <h2>{{ picked.destination.label }}</h2>
      <p class="muted">{{ journey.route.distanceKm.toFixed(1) }} km · about {{ journey.route.durationMinutes }} min walk</p>
      <button type="button" class="primary-button" @click="startWalk">Start walk</button>
    </section>

    <footer class="rewards-footer">Points and visits are saved on this device only. No account needed.</footer>
  </main>
</template>

<style scoped>
.rewards-page {
  max-width: 980px;
  margin: 0 auto;
  padding: 24px 20px 40px;
  display: grid;
  gap: 16px;
  font-family: 'Figtree', system-ui, sans-serif;
  color: #1d2a1d;
  background: #f5f2e8;
}
.card {
  background: white;
  border: 1px solid #e6e1d0;
  border-radius: 20px;
  padding: 18px 20px;
}
.eyebrow {
  display: block;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  color: #1f5a2c;
}
h1,
h2 {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 700;
  margin: 4px 0;
}
h1 {
  font-size: 2.4rem;
}
h2 {
  font-size: 1.3rem;
}
.muted {
  margin: 0;
  color: #6b766a;
  font-size: 0.9rem;
}
.badges {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: grid;
  gap: 10px;
}
.friend {
  display: inline-block;
  margin: 4px 0 0;
  font-weight: 800;
  background: #e4eee4;
  color: #164e29;
  border-radius: 999px;
  padding: 3px 10px;
  animation: pop 500ms ease-out;
}
@keyframes pop {
  0% {
    transform: scale(0.6);
    opacity: 0;
  }
  70% {
    transform: scale(1.08);
    opacity: 1;
  }
  100% {
    transform: scale(1);
  }
}
.route {
  display: grid;
  gap: 8px;
  justify-items: start;
}
.primary-button {
  background: #1f5a2c;
  color: white;
  border: none;
  border-radius: 999px;
  padding: 11px 20px;
  font-family: inherit;
  font-weight: 700;
  font-size: 0.88rem;
  cursor: pointer;
}
.rewards-footer {
  font-size: 0.8rem;
  color: #6b766a;
}
@media (prefers-reduced-motion: reduce) {
  .friend {
    animation: none;
  }
}
</style>
