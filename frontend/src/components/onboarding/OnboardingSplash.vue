<script setup lang="ts">
defineEmits<{ continue: [] }>()
</script>

<template>
  <section class="splash">
    <p class="eyebrow">Stressed?</p>
    <button type="button" class="cta" @click="$emit('continue')">Touch Grass</button>
    <p class="hint">Take a minute to find a greener spot near you.</p>
  </section>
</template>

<style scoped>
.splash {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 24px;
  text-align: center;
  background: var(--tg-cream);
}

.eyebrow {
  margin: 0;
  color: var(--tg-text);
  font-size: 1.1rem;
  font-weight: 600;
}

.cta {
  padding: 4px 8px;
  border: none;
  background: none;
  color: var(--tg-green-700);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: clamp(2.6rem, 8vw, 4.5rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  cursor: pointer;
  transition: color 160ms ease;
}

.cta:hover,
.cta:focus-visible {
  color: var(--tg-green-950);
}

.hint {
  margin: 0;
  max-width: 320px;
  color: var(--tg-muted);
  font-size: 0.85rem;
}
</style>
