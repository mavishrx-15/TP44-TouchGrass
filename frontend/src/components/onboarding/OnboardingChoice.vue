<script setup lang="ts">
defineProps<{
  title: string
  question: string
  options: { value: string; label: string; hint?: string }[]
  modelValue: string | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  next: []
  back: []
}>()
</script>

<template>
  <section class="question-step">
    <div class="question-card">
      <p class="question-title">{{ title }}</p>
      <h1 class="question-text">{{ question }}</h1>

      <div class="choice-grid" role="radiogroup" :aria-label="question">
        <button
          v-for="option in options"
          :key="option.value"
          type="button"
          class="choice-chip"
          :class="{ active: option.value === modelValue }"
          role="radio"
          :aria-checked="option.value === modelValue"
          @click="emit('update:modelValue', option.value)"
        >
          <span class="choice-label">{{ option.label }}</span>
          <span v-if="option.hint" class="choice-hint">{{ option.hint }}</span>
        </button>
      </div>

      <div class="question-actions">
        <button type="button" class="link-button" @click="emit('back')">Back</button>
        <button type="button" class="primary-button" :disabled="!modelValue" @click="emit('next')">
          Continue
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* Mirrors OnboardingQuestion.vue's card so the flow reads as one continuous
   sequence rather than two different question styles. */
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
  margin: 0 0 28px;
  color: var(--tg-green-950);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: clamp(1.5rem, 4vw, 1.9rem);
  line-height: 1.3;
}

.choice-grid {
  display: grid;
  gap: 10px;
}

.choice-chip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 14px 18px;
  border: 1.5px solid var(--tg-green-500);
  border-radius: 12px;
  background: transparent;
  color: var(--tg-text);
  font-size: 0.95rem;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
  transition:
    background 140ms ease,
    color 140ms ease,
    transform 140ms ease;
}

.choice-chip:hover {
  transform: translateY(-1px);
}

.choice-chip.active {
  background: var(--tg-green-700);
  border-color: var(--tg-green-700);
  color: white;
}

.choice-hint {
  color: inherit;
  opacity: 0.75;
  font-size: 0.76rem;
  font-weight: 600;
}

.question-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 30px;
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
  transition:
    background 140ms ease,
    opacity 140ms ease;
}

.primary-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.primary-button:not(:disabled):hover,
.primary-button:not(:disabled):focus-visible {
  background: var(--tg-green-950);
}
</style>
