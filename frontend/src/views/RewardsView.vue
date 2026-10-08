<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import NearbyAreas from '@/components/rewards/NearbyAreas.vue'
import SproutWardrobe from '@/components/rewards/SproutWardrobe.vue'
import VisitHistory from '@/components/rewards/VisitHistory.vue'
import JourneyHeader from '@/components/JourneyHeader.vue'
import { useJourneyStore } from '@/stores/journey'
import { useRewardsStore } from '@/stores/rewards'
import {
  CANOPY_FRIEND_DAYS,
  POINTS_PER_WALK,
  canopyFriendProgress,
  type Visit,
} from '@/services/rewards.logic'
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
  if (await journey.growSproutRoute(area.destination.zoneId)) picked.value = area
}

function startWalk() {
  router.push('/walk')
}
</script>

<template>
  <JourneyHeader />
  <main id="main-content" class="rewards-page">
    <div class="page-intro">
      <span class="eyebrow">YOUR LITTLE GREEN ADVENTURES</span>
      <h1>Good things grow with a walk.</h1>
      <p class="muted">A new leaf, a familiar tree, a little time for you.</p>
    </div>
    <section class="card summary">
      <span class="eyebrow">LEAF POINTS</span>
      <h2 class="points-total">{{ rewards.state.points }}</h2>
      <p class="muted">
        You earn {{ POINTS_PER_WALK }} leaf points for each walk you finish. One walk per area per
        day counts.
      </p>
    </section>

    <section class="card wardrobe-card"><SproutWardrobe /></section>
    <section class="card history-card"><VisitHistory /></section>

    <section class="card">
      <span class="eyebrow">VISITS AND BADGES</span>
      <p v-if="badges.length === 0" class="muted">
        Finish a walk and your visits will show up here, with a Canopy Friend badge after three in a
        week.
      </p>
      <ul v-else class="badges">
        <li v-for="badge in badges" :key="badge.zoneId">
          <strong>{{ badge.label }}</strong>
          <span class="muted"> · {{ badge.visits }} visit{{ badge.visits === 1 ? '' : 's' }}</span>
          <p v-if="badge.friend.earned" class="friend">Canopy Friend</p>
          <p v-else-if="badge.first" class="muted">
            You helped care for this area. Visit {{ badge.friend.visitsNeeded }} more times this
            week to become a Canopy Friend.
          </p>
          <p v-else class="muted">
            Visit {{ badge.friend.visitsNeeded }} more time{{
              badge.friend.visitsNeeded === 1 ? '' : 's'
            }}
            within {{ CANOPY_FRIEND_DAYS }} days to become a Canopy Friend.
          </p>
        </li>
      </ul>
    </section>

    <section class="card">
      <NearbyAreas @pick="choose" />
    </section>

    <section v-if="picked && journey.sproutRoute" class="card route" aria-label="Picked route">
      <span class="eyebrow">PERSONALISED WALKING ROUTE</span>
      <h2>{{ picked.destination.label }}</h2>
      <p class="muted">
        {{ (journey.sproutRoute.distanceMeters / 1000).toFixed(1) }} km · about
        {{ journey.sproutRoute.durationMinutes }} min walk
      </p>
      <button type="button" class="primary-button" @click="startWalk">Start walk</button>
    </section>
    <p v-if="journey.sproutRouteLoading" class="muted" role="status">Growing your next route…</p>
    <p v-if="journey.sproutRouteError" class="route-error" role="alert">
      {{ journey.sproutRouteError }}
    </p>

    <footer class="rewards-footer">
      Points and visits are saved on this device only. No account needed.
    </footer>
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
.page-intro {
  padding: 12px 0 8px;
  grid-column: 1 / -1;
}
.page-intro h1 {
  font-size: clamp(1.7rem, 4vw, 2.5rem);
  max-width: 600px;
  line-height: 1.15;
  margin: 9px 0 12px;
}
.summary {
  background: linear-gradient(120deg, #e6efd9, #f5f8eb);
  grid-column: 1 / -1;
}
.summary .points-total {
  font-size: 3.25rem;
  line-height: 1.15;
  color: #1f5a2c;
}
@media (min-width: 800px) {
  .summary {
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 0 24px;
    align-items: center;
  }
  .summary > .muted {
    grid-column: 2;
    grid-row: 1 / 3;
    max-width: 520px;
  }
}
.wardrobe-card {
  grid-column: 1 / -1;
}
.route-error {
  color: #8a4a12;
}
@media (min-width: 800px) {
  .rewards-page {
    grid-template-columns: 1fr 1fr;
  }
  .rewards-footer,
  .route {
    grid-column: 1 / -1;
  }
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
