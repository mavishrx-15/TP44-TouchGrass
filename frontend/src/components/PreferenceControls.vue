<script setup lang="ts">
import { ref } from 'vue'
import { useJourneyStore } from '@/stores/journey'
import PreferenceInfoDialog from '@/components/PreferenceInfoDialog.vue'
const journey = useJourneyStore()
const activeInfo = ref<'canopy' | 'shade' | null>(null)
const priorities = [
  { key: 'canopy', label: 'Tree Canopy' },
  { key: 'shade', label: 'Shade' },
  { key: 'noise', label: 'Noise avoidance' },
  { key: 'allergy', label: 'Allergy avoidance' },
] as const
const genera = [
  'Eucalyptus',
  'Acacia',
  'Ulmus',
  'Platanus',
  'Corymbia',
  'Allocasuarina',
  'Casuarina',
  'Quercus',
  'Other',
]
</script>
<template>
  <section aria-label="Your preferences">
    <div class="preference-grid">
      <div v-for="item in priorities" :key="item.key" class="preference-field">
        <div class="preference-label">
          <label :id="`priority-${item.key}`">{{ item.label }}</label
          ><button
            v-if="item.key === 'canopy' || item.key === 'shade'"
            type="button"
            class="text-action"
            :aria-label="`About ${item.label}`"
            @click="activeInfo = item.key"
          >
            ⓘ
          </button>
        </div>
        <ElSlider
          v-model="journey.preferences[item.key]"
          :min="0"
          :max="5"
          :step="1"
          show-stops
          :aria-label="item.label"
        />
        <small>{{
          journey.preferences[item.key] === 0
            ? 'No preference'
            : `Priority ${journey.preferences[item.key]} of 5`
        }}</small>
      </div>
    </div>
    <div v-if="journey.preferences.allergy > 0" class="avoidance-fields">
      <label class="field-label"
        >Tree genera to avoid<ElSelect
          v-model="journey.preferences.avoidGenera"
          multiple
          placeholder="Choose genera"
          aria-label="Tree genera to avoid"
          ><ElOption v-for="genus in genera" :key="genus" :label="genus" :value="genus" /></ElSelect
      ></label>
      <label class="field-label"
        >Tree families to avoid<ElSelect
          v-model="journey.preferences.avoidFamilies"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="Type a family, e.g. Myrtaceae"
          aria-label="Tree families to avoid"
      /></label>
      <p v-if="!journey.allergyValid" class="form-error" role="alert">
        Choose at least one genus or family to avoid.
      </p>
      <small>Matches your chosen tree categories; does not measure pollen levels.</small>
    </div>
    <label class="field-label walking-time"
      >Walking Time
      <ElInputNumber
        v-model="journey.preferences.walkingMinutes"
        :min="5"
        :max="180"
        :step="5"
        :precision="0"
        :value-on-clear="30"
        aria-label="Walking time in minutes"
      />
      minutes</label
    >
    <PreferenceInfoDialog :active-info="activeInfo" @close="activeInfo = null" />
  </section>
</template>
<style scoped>
.preference-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px 40px;
}
.preference-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 700;
}
.preference-field small {
  color: var(--tg-muted);
}
.avoidance-fields {
  display: grid;
  gap: 16px;
  margin: 24px 0;
}
.walking-time {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 28px;
  flex-wrap: wrap;
}
@media (max-width: 520px) {
  .preference-grid {
    grid-template-columns: 1fr;
  }
}
</style>
