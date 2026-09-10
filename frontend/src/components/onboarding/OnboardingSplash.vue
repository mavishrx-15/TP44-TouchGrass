<script setup lang="ts">
defineEmits<{ personalise: []; skip: [] }>()
</script>

<template>
  <section class="splash">
    <p class="eyebrow">Stressed?</p>
    <h1 class="headline">Touch Grass</h1>
    <p class="hook">
      A few minutes under real tree cover can lower your stress. We'll find you the nearest patch.
    </p>

    <div class="entry-choice">
      <button type="button" class="primary-button" @click="$emit('personalise')">
        Get my spot
      </button>
      <button type="button" class="link-button" @click="$emit('skip')">
        Just show me the map
      </button>
    </div>
  </section>
</template>

<style scoped>
.splash {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  padding: 24px;
  text-align: center;
  background: var(--tg-cream);
}

.eyebrow {
  margin: 0;
  color: var(--tg-text);
  font-size: clamp(1.3rem, 3.4vw, 1.7rem);
  font-weight: 600;
}

.headline {
  margin: 0;
  color: var(--tg-green-700);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: clamp(3.4rem, 11vw, 5.8rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1;
}

.hook {
  margin: 4px 0 0;
  max-width: 380px;
  color: var(--tg-muted);
  font-size: 0.95rem;
  line-height: 1.5;
}

.entry-choice {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
}

.primary-button {
  padding: 14px 34px;
  border: none;
  border-radius: 12px;
  background: var(--tg-green-700);
  color: white;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease;
}

.primary-button:hover,
.primary-button:focus-visible {
  background: var(--tg-green-950);
}

.link-button {
  padding: 6px 4px;
  border: none;
  background: none;
  color: var(--tg-muted);
  font-size: 0.85rem;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}

.link-button:hover,
.link-button:focus-visible {
  color: var(--tg-text);
}
</style>
