<script setup lang="ts">
import { computed, ref } from 'vue'
import { MOOD_OPTIONS, type Mood } from '@/data/sproutMessages'
import { checkInReply, moodChangeSummary } from '@/data/walkMessages'

/**
 * US6.6: rate how stressed you feel now. If Epic 5 captured a mood before the
 * walk, the before and after sit side by side. If not, only "Now" shows.
 * Rating is optional - "Skip" logs the walk without recording a mood.
 */
const props = defineProps<{ before: Mood | null }>()
const emit = defineEmits<{ log: [after: Mood | null] }>()

const now = ref<Mood | null>(null)
const beforeOption = computed(
  () => MOOD_OPTIONS.find((option) => option.value === props.before) ?? null,
)
const nowOption = computed(() => MOOD_OPTIONS.find((option) => option.value === now.value) ?? null)
const change = computed(() =>
  props.before && now.value ? moodChangeSummary(props.before, now.value) : null,
)
const reply = computed(() => {
  if (change.value) return checkInReply(change.value.direction)
  if (beforeOption.value) {
    return `Before your walk you said you felt ${beforeOption.value.label.toLowerCase()}. How about now?`
  }
  return 'How stressed do you feel now?'
})

function log() {
  if (now.value) emit('log', now.value)
}
function skip() {
  emit('log', null)
}
</script>

<template>
  <section class="check-in">
    <p class="sprout-line" role="status">{{ reply }}</p>
    <h3>How stressed do you feel now?</h3>

    <div class="mood-grid" role="group" aria-label="How stressed you feel now">
      <button
        v-for="option in MOOD_OPTIONS"
        :key="option.value"
        type="button"
        class="mood-option"
        :class="{ selected: now === option.value }"
        :aria-pressed="now === option.value"
        @click="now = option.value"
      >
        <svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true">
          <circle cx="20" cy="20" r="18" :fill="option.color" />
          <circle cx="14" cy="17" r="2.2" fill="#2b2118" />
          <circle cx="26" cy="17" r="2.2" fill="#2b2118" />
          <path
            :d="option.mouth"
            stroke="#2b2118"
            stroke-width="2.4"
            fill="none"
            stroke-linecap="round"
          />
        </svg>
        <span>{{ option.label }}</span>
      </button>
    </div>

    <!-- Before and now, side by side, only when Epic 5 recorded a mood -->
    <div v-if="beforeOption && nowOption" class="compare">
      <div class="side">
        <span class="label">Before your walk</span>
        <strong>{{ beforeOption.label }}</strong>
      </div>
      <div class="side">
        <span class="label">Now</span>
        <strong>{{ nowOption.label }}</strong>
      </div>
      <p class="summary">{{ change?.text }}</p>
    </div>
    <div v-else-if="nowOption" class="now-only">
      <span class="label">Now</span>
      <strong>{{ nowOption.label }}</strong>
    </div>

    <div class="actions">
      <button type="button" class="primary-button" :disabled="!now" @click="log">
        {{ now ? 'Log my visit' : 'Pick how you feel first' }}
      </button>
      <button type="button" class="text-button" @click="skip">Skip</button>
    </div>
  </section>
</template>

<style scoped>
.check-in {
  display: grid;
  gap: 14px;
}
.sprout-line {
  margin: 0;
  font-weight: 600;
  color: var(--tg-green-950);
  line-height: 1.45;
}
h3 {
  margin: 0;
  font-size: 1rem;
}
.mood-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}
.mood-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  border: 2px solid var(--tg-border);
  border-radius: 14px;
  padding: 12px 6px;
  background: white;
  font-size: 0.75rem;
  font-weight: 650;
  cursor: pointer;
  text-align: center;
}
.mood-option.selected {
  border-color: var(--tg-green-700);
  background: var(--tg-green-50);
}
.compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  border: 1px solid var(--tg-border);
  border-radius: 14px;
  padding: 12px;
}
.side {
  display: grid;
  gap: 2px;
}
.summary {
  grid-column: 1 / -1;
  margin: 0;
  font-weight: 700;
  color: var(--tg-green-900);
}
.now-only {
  display: grid;
  gap: 2px;
}
.label {
  font-size: 0.8rem;
  font-weight: 700;
  color: #6b766a;
}
.eyebrow {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: var(--tg-green-700);
}
.actions {
  display: flex;
  align-items: center;
  gap: 14px;
}
.primary-button {
  background: var(--tg-green-800);
  color: white;
  border: none;
  border-radius: 999px;
  padding: 13px 22px;
  font-weight: 700;
  cursor: pointer;
  justify-self: start;
}
.text-button {
  background: none;
  border: none;
  color: var(--tg-green-700);
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}
.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
