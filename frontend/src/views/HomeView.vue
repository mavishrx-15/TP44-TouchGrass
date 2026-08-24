<script setup lang="ts">
import { ElMessage } from 'element-plus'
import AppHeader from '@/components/AppHeader.vue'
import GreenPlaceCard from '@/components/GreenPlaceCard.vue'
import HeroSearch from '@/components/HeroSearch.vue'
import QuickActionCard from '@/components/QuickActionCard.vue'
import StatCard from '@/components/StatCard.vue'

const stats = [
  { icon: '🌳', value: '1,247', label: 'Nearby Trees', detail: 'Trees mapped within 500m' },
  { icon: '🏞️', value: '6', label: 'Tree-Dense Zones', detail: 'High-density clusters nearby' },
  { icon: '🌿', value: '14', label: 'Species Found', detail: 'Distinct species in area' },
  {
    icon: '🩺',
    value: '4',
    label: 'Community Reports',
    detail: 'Tree health reports nearby',
    neutral: true,
  },
]

const actions = [
  {
    icon: '🗺️',
    title: 'Explore Green Map',
    description: 'See tree canopy, heat spots and green spaces near you.',
    to: '/map',
  },
  {
    icon: '🚶',
    title: 'Find a Green Path',
    description: 'Choose a shadier, greener route to your destination.',
    to: '/map',
  },
  {
    icon: '🔍',
    title: 'Identify a Tree',
    description: "Upload a photo and we'll help identify the species.",
    to: '/identify-tree',
  },
  {
    icon: '🩺',
    title: 'Report Tree Health',
    description: 'Help care for local trees by reporting health issues.',
    to: '/tree-health',
  },
]

const places = [
  {
    name: 'Royal Park',
    distance: '1.8 km',
    trees: '120+',
    density: 'High density' as const,
    description:
      'Native vegetation reserve with walking paths, mapped tree locations and wildlife.',
    scene: 'park' as const,
  },
  {
    name: 'Riverside Park',
    distance: '0.8 km',
    trees: '89+',
    density: 'High density' as const,
    description:
      'A peaceful park along the Maribyrnong with large river red gums and riverside walks.',
    scene: 'river' as const,
  },
  {
    name: 'Princes Park',
    distance: '1.2 km',
    trees: '60+',
    density: 'Medium density' as const,
    description:
      'Formal gardens with a significant heritage tree collection and open green spaces.',
    scene: 'garden' as const,
  },
]

function exploreArea(suburb: string) {
  ElMessage.success(`Showing green spaces around ${suburb}`)
  document.querySelector('#neighbourhood')?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<template>
  <AppHeader />
  <main>
    <HeroSearch @explore="exploreArea" />

    <section id="neighbourhood" class="content-section neighbourhood-section">
      <div class="page-container">
        <div class="section-heading">
          <h2 class="section-title">Your Neighbourhood — Kensington</h2>
          <span>Based on City of Melbourne tree location data</span>
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
          <h2 class="section-title">Tree-Dense Places Near You</h2>
          <ElTag round type="success" effect="plain">Sorted by: Tree Density ↓</ElTag>
        </div>
        <div class="places-grid">
          <GreenPlaceCard v-for="place in places" :key="place.name" v-bind="place" />
        </div>
      </div>
    </section>

    <section class="tip-section">
      <div class="page-container">
        <div class="green-tip">
          <span class="tip-icon" aria-hidden="true">🌿</span>
          <div>
            <strong>Today's green tip</strong>
            <p>
              Trees can lower local air temperature by up to 8°C — seek mature canopy on hot days.
            </p>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.content-section {
  padding-top: 56px;
}

.neighbourhood-section {
  scroll-margin-top: 64px;
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
  font-size: 0.7rem;
}

.stats-grid,
.actions-grid,
.places-grid {
  display: grid;
  margin-top: 20px;
  gap: 18px;
}

.stats-grid,
.actions-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.places-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.places-section {
  scroll-margin-top: 64px;
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

@media (max-width: 920px) {
  .stats-grid,
  .actions-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

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
