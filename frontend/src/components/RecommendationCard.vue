<script setup lang="ts">
import { computed, ref } from 'vue'
import GoogleMapCanvas from './GoogleMapCanvas.vue'
import { USE_MOCK_DATA } from '@/services/personalisation.service'
import { canopyLabel, noiseLabel, shadeLabel } from '@/services/preferences'
import type { Recommendation } from '@/types/personalisation'
const props = defineProps<{ area: Recommendation; best: boolean; busy?: boolean }>()
const emit = defineEmits<{ navigate: [] }>()
const mapError = ref('')
const matched = computed(() => props.area.match.matches.filter((item) => item.matched))
const partial = computed(() => props.area.match.matches.filter((item) => !item.matched))
// Several zones in the same precinct can lack a nearestStreet, so their label
// falls back to the precinct name alone (AC4) - multiple cards can then share
// a heading. This adds a visible, non-invented distinguisher without changing
// that shared label.
const areaDistinguisher = computed(() =>
  props.area.nearestStreet
    ? null
    : props.area.dominantGenus
      ? `${props.area.dominantGenus} tree cluster`
      : `${props.area.density}-density area`,
)
</script>
<template>
  <article
    class="recommendation-card"
    :class="{ best }"
    :aria-label="`${best ? 'Best match: ' : ''}${area.label}${areaDistinguisher ? ` — ${areaDistinguisher}` : ''}`"
  >
    <div class="card-heading">
      <span v-if="best" class="best-badge">Best match</span>
      <h2>{{ area.label }}</h2>
      <p v-if="areaDistinguisher" class="area-distinguisher">{{ areaDistinguisher }}</p>
      <p>
        {{ area.treeCount }} trees · {{ canopyLabel(area.metrics.canopy) }} canopy ·
        {{ area.distanceKm.toFixed(1) }} km · ~{{ area.estimatedMinutes }} min walk
      </p>
    </div>
    <div class="area-map">
      <div aria-hidden="true">
        <GoogleMapCanvas
          :center="area.center"
          :destination="area.center"
          :trees="area.trees ?? []"
          :zones="[area]"
          :directions-open="false"
          :route-options="[]"
          :demo="USE_MOCK_DATA"
          compact
          @error="mapError = $event"
        />
      </div>
      <span v-if="mapError" class="thumbnail-error"
        >Map unavailable · {{ area.center.lat.toFixed(3) }}, {{ area.center.lng.toFixed(3) }}</span
      >
    </div>
    <div class="preference-chips">
      <span
        v-for="match in area.match.matches.slice(0, 3)"
        :key="match.key"
        class="preference-chip"
        :class="{ partial: !match.matched }"
        >{{ match.matched ? '✓' : '◷' }} {{ match.label
        }}{{ match.matched ? '' : ' — partial' }}</span
      >
    </div>
    <p class="area-reason">{{ area.match.sentence }}</p>
    <section class="card-section">
      <h3>Area overview</h3>
      <dl class="area-overview">
        <div>
          <dt>Precinct</dt>
          <dd>{{ area.precinctName }}</dd>
        </div>
        <div>
          <dt>Nearby street</dt>
          <dd>{{ area.nearestStreet ?? 'Not available' }}</dd>
        </div>
        <div>
          <dt>Tree density</dt>
          <dd>{{ area.density }}</dd>
        </div>
        <div>
          <dt>Tree count</dt>
          <dd>{{ area.treeCount }}</dd>
        </div>
        <div>
          <dt>Tree canopy</dt>
          <dd>{{ canopyLabel(area.metrics.canopy) }}</dd>
        </div>
        <div>
          <dt>Shade / thermal</dt>
          <dd>{{ shadeLabel(area.metrics.parkShare) }}</dd>
        </div>
        <div>
          <dt>Noise level</dt>
          <dd>{{ noiseLabel(area.metrics.parkShare) }}</dd>
        </div>
        <div>
          <dt>Estimated walk</dt>
          <dd>~{{ area.estimatedMinutes }} min · {{ area.distanceKm.toFixed(1) }} km</dd>
        </div>
      </dl>
      <p class="distance-note">
        Distance is measured from your starting point, in a straight line. Walking time is an
        estimate.
      </p>
      <p v-for="note in area.dataNotes" :key="note" class="data-note">⚑ {{ note }}</p>
    </section>
    <section class="card-section">
      <h3>Tree information</h3>
      <ul class="tree-genera">
        <li
          v-for="(genus, index) in area.genera"
          :key="genus.name"
          :class="{ dominant: index === 0 }"
        >
          <span><small v-if="index === 0">Dominant</small>{{ genus.name }}</span
          ><strong>{{ genus.count }} trees</strong>
        </li>
      </ul>
      <p v-if="!area.genera.length" class="distance-note">
        Tree composition is not available for this area.
      </p>
    </section>
    <section class="card-section match-section">
      <h3>Why this area matches you</h3>
      <template v-if="matched.length"
        ><h4>Matches</h4>
        <ul>
          <li v-for="match in matched" :key="match.key">
            <span class="match-symbol">✓</span
            ><span
              >{{ match.label }}<small>{{ match.detail }}</small></span
            >
          </li>
        </ul></template
      >
      <template v-if="partial.length"
        ><h4 class="partial-heading">Does not fully match</h4>
        <ul>
          <li v-for="match in partial" :key="match.key">
            <span class="partial-symbol">◷</span
            ><span
              >{{ match.label }}<small>{{ match.detail }}</small></span
            >
          </li>
        </ul></template
      >
      <p v-if="!area.match.matches.length" class="distance-note">
        No preferences selected. This nearby area gives you a place to start.
      </p>
    </section>
    <button
      type="button"
      class="primary-button navigate-button"
      :disabled="busy"
      @click="emit('navigate')"
    >
      {{ busy ? 'Preparing route…' : 'Navigate' }}
    </button>
  </article>
</template>
<style scoped>
.recommendation-card {
  background: white;
  border: 1px solid var(--tg-border);
  border-radius: 14px;
  padding: 18px;
  min-width: 0;
  align-self: start;
}
.recommendation-card.best {
  border: 2px solid var(--tg-green-700);
  padding: 17px;
  box-shadow: 0 10px 25px #2441220d;
}
.best-badge {
  display: inline-block;
  text-transform: uppercase;
  background: var(--tg-green-800);
  color: white;
  border-radius: 20px;
  font-weight: 800;
  font-size: 0.58rem;
  padding: 4px 8px;
  margin-bottom: 6px;
}
h2 {
  font:
    bold 1.17rem/1.22 Georgia,
    serif;
  color: var(--tg-green-950);
  margin: 0 0 5px;
}
.card-heading > .area-distinguisher {
  color: var(--tg-green-800);
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  margin: 0 0 6px;
}
.card-heading > p {
  color: var(--tg-muted);
  font-size: 0.69rem;
  margin: 0 0 15px;
  line-height: 1.6;
}
.area-map {
  height: 115px;
  position: relative;
  overflow: hidden;
  border-radius: 10px;
  background: #eef1e7;
  margin-bottom: 13px;
}
.thumbnail-error {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  text-align: center;
  font-size: 0.7rem;
  padding: 15px;
  color: var(--tg-muted);
}
.preference-chips {
  gap: 4px;
}
.preference-chip {
  font-size: 0.61rem;
  padding: 3px 6px;
}
.area-reason {
  font-size: 0.74rem;
  line-height: 1.6;
  margin: 12px 0 16px;
}
.card-section {
  border-top: 1px solid var(--tg-border);
  padding-top: 14px;
  margin-top: 14px;
}
h3 {
  text-transform: uppercase;
  font-size: 0.73rem;
  font-weight: 800;
  margin: 0 0 12px;
  color: var(--tg-green-950);
}
.area-overview {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
  margin: 0;
}
.area-overview dt {
  text-transform: uppercase;
  font-size: 0.57rem;
  font-weight: 750;
  color: var(--tg-muted);
  margin-bottom: 3px;
}
.area-overview dd {
  margin: 0;
  font-size: 0.73rem;
  line-height: 1.35;
  font-weight: 650;
}
.data-note {
  color: #967020;
  font-size: 0.61rem;
  line-height: 1.6;
  margin: 8px 0 0;
}
.distance-note {
  color: var(--tg-muted);
  font-size: 0.65rem;
  line-height: 1.55;
  margin: 10px 0 0;
}
.tree-genera {
  list-style: none;
  padding: 0;
  margin: 0;
}
.tree-genera li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 9px;
  font-size: 0.73rem;
}
.tree-genera li.dominant {
  border-radius: 6px;
  background: var(--tg-green-50);
  font-weight: 700;
}
.tree-genera small {
  display: block;
  font-size: 0.55rem;
  color: var(--tg-green-800);
  text-transform: uppercase;
}
.tree-genera strong {
  font-size: 0.64rem;
  color: var(--tg-muted);
  font-weight: 500;
}
.tree-genera .dominant strong {
  color: var(--tg-green-800);
  font-weight: 750;
}
.match-section h4 {
  margin: 11px 0 6px;
  text-transform: uppercase;
  color: var(--tg-green-800);
  font-size: 0.57rem;
}
.match-section h4.partial-heading {
  color: #946a1c;
}
.match-section ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
.match-section li {
  display: flex;
  align-items: start;
  gap: 6px;
  font-size: 0.71rem;
  line-height: 1.5;
  margin: 6px 0;
}
.match-section li small {
  display: block;
  color: var(--tg-muted);
  font-size: 0.65rem;
}
.match-symbol {
  color: var(--tg-green-700);
}
.partial-symbol {
  color: #946a1c;
}
.navigate-button {
  min-height: 40px;
  margin-top: 16px;
  font-size: 0.76rem;
  border-radius: 8px;
}
@media (max-width: 760px) {
  .recommendation-card {
    padding: 20px;
  }
  .recommendation-card.best {
    padding: 19px;
  }
  h2 {
    font-size: 1.3rem;
  }
  .card-heading > p,
  .area-reason {
    font-size: 0.79rem;
  }
  .area-map {
    height: 140px;
  }
  .preference-chip {
    font-size: 0.67rem;
  }
  .area-overview dd {
    font-size: 0.82rem;
  }
  .area-overview dt {
    font-size: 0.65rem;
  }
  h3 {
    font-size: 0.8rem;
  }
  .tree-genera li,
  .match-section li {
    font-size: 0.8rem;
  }
  .data-note,
  .distance-note,
  .match-section li small {
    font-size: 0.71rem;
  }
  .navigate-button {
    min-height: 46px;
    font-size: 0.86rem;
  }
}
</style>
