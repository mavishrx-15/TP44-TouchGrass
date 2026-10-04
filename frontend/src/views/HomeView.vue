<script setup lang="ts">
import { onMounted, ref } from 'vue'
import JourneyHeader from '@/components/JourneyHeader.vue'
import DemoNotice from '@/components/DemoNotice.vue'
import LeafIcon from '@/components/LeafIcon.vue'
import SproutGuide from '@/components/sprout/SproutGuide.vue'
import { useJourneyStore } from '@/stores/journey'

const journey = useJourneyStore()
const initError = ref('')
async function initialize() {
  initError.value = ''
  try {
    await journey.initialize()
  } catch {
    initError.value = 'We couldn’t load covered areas. Please try again.'
  }
}
onMounted(initialize)
</script>

<template>
  <JourneyHeader />
  <DemoNotice />
  <main id="main-content" tabindex="-1" class="home-page">
    <section class="home-hero">
      <div class="hero-copy">
        <span class="eyebrow">Less stress. More green.</span>
        <h1>Feeling overwhelmed?<br />Take a greener route.</h1>
        <p>
          Tell us what you need right now, and we’ll find a<br class="desktop-break" />
          route that helps you slow down and reset.
        </p>
      </div>
      <svg
        class="canopy-motif"
        viewBox="0 0 1440 170"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path
          fill="#c9e3ae"
          d="M0 100 Q80 20 160 72 T320 80 T480 90 T640 70 T800 74 T960 85 T1120 58 T1280 86 T1440 54 V170 H0Z"
        />
        <path
          fill="#9bc879"
          d="M0 128 Q90 56 180 108 T360 110 T540 122 T720 108 T900 124 T1080 99 T1260 115 T1440 94 V170 H0Z"
        />
      </svg>
    </section>

    <div class="home-form">
      <p v-if="initError" class="form-error" role="alert">
        {{ initError }}
        <button type="button" class="text-button" @click="initialize">Retry</button>
      </p>
      <SproutGuide />
    </div>
    <footer class="home-footer"><span /><LeafIcon />Small changes. A bigger impact.<span /></footer>
  </main>
</template>

<style scoped>
.home-hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(110deg, #f2f8eb, #eef7e3);
  min-height: 284px;
}
.hero-copy {
  position: relative;
  z-index: 1;
  width: min(850px, calc(100% - 48px));
  margin: auto;
  padding: 36px 0 70px;
}
h1 {
  margin: 12px 0 14px;
  font:
    bold clamp(1.8rem, 3.6vw, 2.6rem)/1.08 Georgia,
    serif;
  color: var(--tg-green-950);
  letter-spacing: -0.025em;
}
.hero-copy > p {
  margin: 0;
  font-size: 0.96rem;
  line-height: 1.5;
  max-width: 450px;
}
.canopy-motif {
  position: absolute;
  inset: auto 0 0;
  width: 100%;
  height: 100px;
}
.home-form {
  width: min(850px, calc(100% - 48px));
  margin: 22px auto 0;
}
.form-error {
  color: #b44235;
  font-size: 0.82rem;
  margin: 0 0 12px;
}
.text-button {
  background: none;
  border: none;
  color: var(--tg-green-700);
  font-weight: 700;
  font-size: 0.78rem;
  cursor: pointer;
}
.home-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 28px 15px;
  font-size: 0.66rem;
  color: var(--tg-muted);
  font-weight: 700;
  letter-spacing: 0.055em;
  text-transform: uppercase;
}
.home-footer > span {
  height: 1px;
  width: 60px;
  background: var(--tg-border);
}
.home-footer svg {
  width: 15px;
  height: 15px;
}
@media (max-width: 600px) {
  .hero-copy,
  .home-form {
    width: calc(100% - 36px);
  }
  .hero-copy {
    padding: 28px 0 66px;
  }
  .home-hero {
    min-height: 244px;
  }
  .canopy-motif {
    height: 68px;
  }
  .hero-copy > p {
    font-size: 0.88rem;
  }
  .home-form {
    margin-top: 17px;
  }
  .home-footer > span {
    width: 25px;
  }
  .home-footer {
    gap: 6px;
    font-size: 0.59rem;
  }
}
</style>
