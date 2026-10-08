<script setup lang="ts">
import { computed, ref } from 'vue'

/**
 * US6.5: a one-minute grounding exercise, four short steps, worded as in the
 * prototype. Skip at any point, or finish step 4, and the walk moves on to
 * pinning a tree (Epic 7).
 */
const emit = defineEmits<{ done: [] }>()

const steps = [
  {
    title: 'Find a tree',
    body: 'Look around and walk to the closest tree you can reach safely. Stand right next to it, then tap the button below.',
    say: 'You made it! First, find a tree near you. Walk to the closest one you can see.',
    action: 'I’m next to a tree',
  },
  {
    title: 'Touch the bark',
    body: 'Rest your hand on the tree you found. Is the bark rough or smooth? Warm or cool?',
    say: 'Found one? Let’s take one quiet minute together.',
    action: 'Next',
  },
  {
    title: 'Listen for 3 sounds',
    body: 'Close your eyes if that feels okay. Name 3 things you can hear. Leaves, birds, footsteps, water.',
    say: 'Beautiful. What did you notice?',
    action: 'Next',
  },
  {
    title: 'Breathe',
    body: 'Follow the circle for 3 slow breaths.',
    say: 'Breathe with me. In as the circle grows, out as it shrinks.',
    action: 'I feel grounded',
  },
] as const

const index = ref(0)
const current = computed(() => steps[index.value]!)
// The breathing circle animates while the user is on step 4, then rests.
const breathing = computed(() => index.value === steps.length - 1)

function advance() {
  if (index.value >= steps.length - 1) {
    emit('done')
    return
  }
  index.value += 1
}
</script>

<template>
  <section class="grounding" aria-live="polite">
    <p class="progress-label">1 MINUTE GROUNDING · {{ index + 1 }} OF {{ steps.length }}</p>
    <div class="ground-card">
      <svg class="icon" viewBox="0 0 40 40" aria-hidden="true">
        <circle cx="20" cy="15" r="11" fill="#5fa150" />
        <rect x="18" y="24" width="4" height="12" rx="1.5" fill="#8a5a3b" />
      </svg>
      <p class="say">{{ current.say }}</p>
      <h3>{{ current.title }}</h3>
      <p class="body">{{ current.body }}</p>

      <div v-if="breathing" class="breath-wrap" aria-hidden="true">
        <div class="breath-circle" :class="{ breathing }" />
        <div class="breath-labels">
          <span class="in">Breathe in</span>
          <span class="out">Breathe out</span>
        </div>
      </div>

      <div class="actions">
        <button type="button" class="text-button" @click="emit('done')">Skip</button>
        <button type="button" class="primary-button" @click="advance">{{ current.action }}</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.grounding {
  display: grid;
  gap: 10px;
  font-family: 'Figtree', system-ui, sans-serif;
  color: #1d2a1d;
}
.ground-card {
  display: grid;
  gap: 10px;
  background: #eef6e7;
  border-radius: 20px;
  padding: 18px 20px 16px;
}
.icon {
  width: 40px;
  height: 40px;
}
.progress-label {
  margin: 0;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #1f5a2c;
}
.say {
  margin: 0;
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.05rem;
  font-weight: 600;
  line-height: 1.35;
}
h3 {
  margin: 4px 0 0;
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.5rem;
}
.body {
  margin: 0;
  line-height: 1.5;
}
.breath-wrap {
  display: grid;
  justify-items: center;
  gap: 8px;
  padding: 10px 0;
}
.breath-circle {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: radial-gradient(circle at 40% 35%, #cfe9bd, #7fb56b);
  transform: scale(0.8);
}
.breath-circle.breathing {
  animation: breathe 12s ease-in-out infinite;
}
.breath-labels {
  position: relative;
  height: 1.2em;
  font-size: 0.8rem;
  font-weight: 700;
  color: #1f5a2c;
}
.breath-labels .in,
.breath-labels .out {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
}
.breath-labels .in {
  animation: show-in 12s linear infinite;
}
.breath-labels .out {
  animation: show-out 12s linear infinite;
}
@keyframes breathe {
  0%,
  40% {
    transform: scale(0.8);
  }
  60%,
  100% {
    transform: scale(1.12);
  }
}
@keyframes show-in {
  0%,
  40% {
    opacity: 1;
  }
  50%,
  100% {
    opacity: 0;
  }
}
@keyframes show-out {
  0%,
  40% {
    opacity: 0;
  }
  50%,
  100% {
    opacity: 1;
  }
}
.actions {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  margin-top: 6px;
}
.primary-button {
  background: #1f5a2c;
  color: white;
  border: none;
  border-radius: 999px;
  padding: 12px 22px;
  font-weight: 700;
  cursor: pointer;
}
.text-button {
  background: none;
  border: none;
  color: #6b766a;
  font-weight: 700;
  cursor: pointer;
}
@media (prefers-reduced-motion: reduce) {
  .breath-circle.breathing,
  .breath-labels .in,
  .breath-labels .out {
    animation: none;
  }
  .breath-labels .out {
    display: none;
  }
}
</style>
