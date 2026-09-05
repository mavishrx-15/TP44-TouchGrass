<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    question: string
    leftLabel: string
    rightLabel: string
    modelValue: number
    steps?: number
  }>(),
  { steps: 7 },
)

const emit = defineEmits<{
  'update:modelValue': [value: number]
  next: []
  back: []
}>()
</script>

<template>
  <section class="question-step">
    <div class="question-card">
      <p class="question-title">{{ title }}</p>
      <h1 class="question-text">{{ question }}</h1>

      <div class="scale" role="radiogroup" :aria-label="question">
        <button
          v-for="value in steps"
          :key="value"
          type="button"
          class="scale-dot"
          :class="{ active: value === modelValue }"
          role="radio"
          :aria-checked="value === modelValue"
          :aria-label="`${value} of ${steps}`"
          @click="emit('update:modelValue', value)"
        />
      </div>
      <div class="scale-labels">
        <span>{{ leftLabel }}</span>
        <span>{{ rightLabel }}</span>
      </div>

      <div class="question-actions">
        <button type="button" class="link-button" @click="emit('back')">Back</button>
        <button type="button" class="primary-button" @click="emit('next')">Continue</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.question-step {
  display: flex;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--tg-cream);
}

.question-card {
  width: min(440px, 100%);
  padding: 40px 32px;
  border: 1px solid var(--tg-border);
  border-radius: 20px;
  background: var(--tg-surface);
  text-align: center;
}

.question-title {
  margin: 0 0 14px;
  color: var(--tg-green-700);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.question-text {
  margin: 0 0 32px;
  color: var(--tg-green-950);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: clamp(1.5rem, 4vw, 1.9rem);
  line-height: 1.3;
}

.scale {
  display: flex;
  justify-content: center;
  gap: 10px;
}

.scale-dot {
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1.5px solid var(--tg-green-500);
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  transition:
    background 140ms ease,
    transform 140ms ease;
}

.scale-dot:hover {
  transform: scale(1.08);
}

.scale-dot.active {
  background: var(--tg-green-700);
  border-color: var(--tg-green-700);
}

.scale-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  color: var(--tg-muted);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.question-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 34px;
}

.link-button {
  padding: 8px 4px;
  border: none;
  background: none;
  color: var(--tg-muted);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}

.link-button:hover,
.link-button:focus-visible {
  color: var(--tg-text);
}

.primary-button {
  padding: 11px 26px;
  border: none;
  border-radius: 10px;
  background: var(--tg-green-700);
  color: white;
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease;
}

.primary-button:hover,
.primary-button:focus-visible {
  background: var(--tg-green-950);
}

@media (max-width: 420px) {
  .scale {
    gap: 6px;
  }

  .scale-dot {
    width: 26px;
    height: 26px;
  }
}
</style>
