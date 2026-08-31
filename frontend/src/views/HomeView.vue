<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import GreenPlaceCard from '@/components/GreenPlaceCard.vue'
import HeroSearch from '@/components/HeroSearch.vue'
import QuickActionCard from '@/components/QuickActionCard.vue'
import StatCard from '@/components/StatCard.vue'
import { useDiscoveryStore } from '@/stores/discovery'

const router = useRouter()
const discovery = useDiscoveryStore()
const { selectedPrecinct, searchError, loadError, isLoading, snapshot, rankedZones } =
  storeToRefs(discovery)

onMounted(() => discovery.initialize())

const featuredZones = computed(() => rankedZones.value.slice(0, 3))

const stats = computed(() => [
  {
    icon: '🌳',
    value: snapshot.value.treeCount.toLocaleString(),
    label: 'Nearby Trees',
    detail: `Trees recorded in ${selectedPrecinct.value.name}`,
  },
  {
    icon: '▦',
    value: snapshot.value.zoneCount.toString(),
    label: 'Tree-Dense Zones',
    detail: `Mapped clusters in ${selectedPrecinct.value.name}`,
  },
  {
    icon: '♧',
    value: snapshot.value.speciesCount.toString(),
    label: 'Species Found',
    detail: 'Distinct recorded scientific names',
  },
])

const actions = [
  {
    icon: '⌖',
    title: 'Explore Green Map',
    description: 'See individual trees and tree-density zones near you.',
    to: '/map',
  },
  {
    icon: '↝',
    title: 'Find a Green Path',
    description: 'Compare a standard walk with a route passing more trees.',
    to: '/map?directions=true',
  },
]

async function exploreArea(precinctName: string) {
  if (!(await discovery.search(precinctName))) return
  router.push('/map')
}
</script>

<template>
  <AppHeader />
  <main>
    <HeroSearch
      :initial-value="selectedPrecinct.name"
      :precincts="discovery.precincts.map((precinct) => precinct.name)"
      @explore="exploreArea"
    />

    <section v-if="searchError" class="error-section">
      <div class="page-container">
        <ElAlert :title="searchError" type="warning" show-icon :closable="false" />
      </div>
    </section>

    <section v-if="loadError" class="error-section">
      <div class="page-container">
        <ElAlert :title="loadError" type="error" show-icon :closable="false" />
      </div>
    </section>

    <section id="neighbourhood" class="content-section neighbourhood-section">
      <div class="page-container">
        <div class="section-heading">
          <h2 class="section-title">Your Neighbourhood — {{ selectedPrecinct.name }}</h2>
          <span>City of Melbourne tree data served by the TouchGrass API</span>
        </div>
        <div class="stats-grid">
          <StatCard v-for="stat in stats" :key="stat.label" v-bind="stat" />
        </div>
      </div>
    </section>

    <section id="actions" class="content-section">
      <div class="page-container">
        <h2 class="section-title">Quick Actions</h2>
        <div class="actions-grid">
          <QuickActionCard v-for="action in actions" :key="action.title" v-bind="action" />
        </div>
      </div>
    </section>

    <section id="places" class="content-section places-section">
      <div class="page-container">
        <div class="places-heading">
          <h2 class="section-title">Tree-Dense Zones Near You</h2>
        </div>
        <div v-loading="isLoading" class="places-results">
          <div v-if="featuredZones.length" class="places-grid">
            <GreenPlaceCard v-for="zone in featuredZones" :key="zone.id" :zone="zone" />
          </div>
          <ElEmpty v-else description="No tree-density zones were found for this precinct." />
        </div>
      </div>
    </section>

    <section class="tip-section">
      <div class="page-container">
        <div class="green-tip">
          <span class="tip-icon" aria-hidden="true">♧</span>
          <div>
            <strong>Today's green tip</strong>
            <p>Trees can lower local air temperature — seek mature canopy on hot days.</p>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.error-section {
  padding-top: 24px;
}

.content-section {
  padding-top: 56px;
}

.neighbourhood-section,
.places-section {
  scroll-margin-top: 76px;
}

.section-heading,
.places-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.section-heading > span {
  color: var(--tg-muted);
  font-size: 0.72rem;
}

.stats-grid,
.actions-grid,
.places-grid {
  display: grid;
  margin-top: 20px;
  gap: 18px;
}

.places-results {
  min-height: 180px;
}

.stats-grid,
.places-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.actions-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.tip-section {
  padding: 46px 0 72px;
}

.green-tip {
  display: flex;
  min-height: 108px;
  align-items: center;
  gap: 24px;
  padding: 24px 34px;
  border: 1px solid #b7db94;
  border-radius: 16px;
  background: var(--tg-green-100);
}

.tip-icon {
  color: var(--tg-green-700);
  font-size: 2rem;
}

.green-tip strong {
  color: var(--tg-green-700);
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.green-tip p {
  margin: 8px 0 0;
  color: var(--tg-text);
  font-size: 0.86rem;
}

@media (max-width: 900px) {
  .stats-grid,
  .places-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .content-section {
    padding-top: 38px;
  }

  .section-heading,
  .places-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }

  .stats-grid,
  .actions-grid,
  .places-grid {
    grid-template-columns: 1fr;
  }

  .green-tip {
    align-items: flex-start;
    padding: 24px;
  }
}
</style>
