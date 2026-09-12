<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Clock, Location, Warning, Headset, InfoFilled } from '@element-plus/icons-vue'
import JourneyHeader from '@/components/JourneyHeader.vue'
import DemoNotice from '@/components/DemoNotice.vue'
import LeafIcon from '@/components/LeafIcon.vue'
import LocationSearch from '@/components/LocationSearch.vue'
import PreferenceInfo from '@/components/PreferenceInfo.vue'
import { useJourneyStore } from '@/stores/journey'
import type { Preferences } from '@/types/personalisation'
import type { Precinct, RoutePlace } from '@/types/discovery'

const journey = useJourneyStore()
const router = useRouter()
const locationInput = ref<InstanceType<typeof LocationSearch> | null>(null)
const activeInfo = ref<'canopy' | 'shade' | null>(null)
const locationError = ref('')
const initError = ref('')
const locating = ref(false)
const submitting = ref(false)
const quickPrecincts = computed(() =>
  ['melbourne', 'melbourne-cbd', 'kensington', 'parkville', 'north-melbourne', 'docklands'].flatMap(
    (id) => journey.precincts.filter((precinct) => precinct.id === id),
  ),
)
const times: { label: string; value: Preferences['walkingTime'] }[] = [
  { label: '5 min', value: 5 },
  { label: '10 min', value: 10 },
  { label: '15 min', value: 15 },
  { label: '20+ min', value: 20 },
  { label: 'No preference', value: null },
]
const noiseOptions: { label: string; value: Preferences['noise'] }[] = [
  { label: 'No preference', value: null },
  { label: 'Quieter surroundings', value: 'quiet' },
  { label: 'Lively atmosphere', value: 'lively' },
]
const allergyOptions: { label: string; value: Preferences['allergy'] }[] = [
  { label: 'No preference', value: null },
  { label: 'Avoid high-pollen areas', value: 'avoid' },
  { label: 'Prefer lower-allergy areas', value: 'lower' },
]
const coverageNotice = computed(() => {
  const coverage = journey.coverage
  return coverage?.outside
    ? `You’re about ${coverage.distanceKm.toFixed(1)} km from ${coverage.precinct.name}, the nearest area we cover. We’ll still show it, but it’ll be a longer trip than a short break usually is.`
    : null
})
async function initialize() {
  initError.value = ''
  try {
    await journey.initialize()
  } catch {
    initError.value = 'We couldn’t load covered areas. Please try again.'
  }
}
async function locate() {
  locating.value = true
  locationError.value = ''
  try {
    await journey.useCurrentLocation()
  } catch (e) {
    locationError.value = e instanceof Error ? e.message : 'Location is unavailable.'
  } finally {
    locating.value = false
  }
}
async function continueToRoute() {
  if (!journey.startLocation) {
    locationError.value = 'Choose an address, an area, or your current location to continue.'
    await nextTick()
    locationInput.value?.focus()
    return
  }
  locationError.value = ''
  submitting.value = true
  try {
    if (await journey.findGreenerRoute()) await router.push('/explore')
  } finally {
    submitting.value = false
  }
}
function setSlider(key: 'canopy' | 'shade', event: Event) {
  journey.preferences[key] = Number((event.target as HTMLInputElement).value)
}
function setOrigin(value: RoutePlace | null) {
  journey.startLocation = value
  locationError.value = ''
}
function choosePrecinct(precinct: Precinct) {
  setOrigin({ id: precinct.id, label: precinct.name, coordinates: precinct.referencePoint })
}
onMounted(initialize)
</script>

<template>
  <JourneyHeader />
  <DemoNotice />
  <main class="home-page">
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

    <form class="home-form" :aria-busy="submitting" @submit.prevent="continueToRoute">
      <div class="preferences-banner">
        <span class="section-icon"><LeafIcon /></span>
        <div>
          <h2>Your preferences</h2>
          <p>We’ll use these to find a route that matches how you want to feel.</p>
        </div>
        <button type="button" class="text-button" @click="journey.skipPersonalisation">
          Skip personalisation →
        </button>
      </div>
      <div class="summary-strip" aria-live="polite">
        <div v-if="journey.summary.length" class="preference-chips">
          <span v-for="chip in journey.summary" :key="chip" class="preference-chip">{{
            chip
          }}</span>
        </div>
        <p v-else>No preferences set yet — everything below is optional.</p>
      </div>

      <section class="preference-card location-card">
        <h2>Where are you starting from?</h2>
        <p class="helper">
          We currently cover tree-dense areas across inner Melbourne. Please search your street or
          precinct below.
        </p>
        <LocationSearch
          ref="locationInput"
          :model-value="journey.startLocation"
          :precincts="journey.precincts"
          :invalid="!!locationError"
          @update:model-value="setOrigin"
        />
        <button type="button" class="location-button" :disabled="locating" @click="locate">
          <ElIcon><Location /></ElIcon
          >{{ locating ? 'Finding your location…' : 'Use my current location' }}
        </button>
        <div class="field-caption">Or choose an area</div>
        <div class="pills area-pills" role="group" aria-label="Starting area">
          <button
            v-for="precinct in quickPrecincts"
            :key="precinct.id"
            type="button"
            :class="{ selected: journey.startLocation?.id === precinct.id }"
            :aria-pressed="journey.startLocation?.id === precinct.id"
            @click="choosePrecinct(precinct)"
          >
            {{ precinct.name }}
          </button>
        </div>
        <p v-if="initError" class="form-error" role="alert">
          {{ initError }}
          <button type="button" class="text-button" @click="initialize">Retry</button>
        </p>
        <p v-if="locationError" class="form-error" role="alert">{{ locationError }}</p>
        <p v-if="coverageNotice" class="notice coverage-notice" role="status">
          <ElIcon><Warning /></ElIcon>{{ coverageNotice }}
        </p>
      </section>

      <section class="preference-card time-card">
        <div class="section-heading">
          <span class="section-icon"
            ><ElIcon><Clock /></ElIcon
          ></span>
          <div>
            <h2>How much time do you have?</h2>
            <p class="helper">Choose a time that works for you.</p>
          </div>
        </div>
        <div class="pills" role="group" aria-label="Walking time">
          <button
            v-for="option in times"
            :key="option.label"
            type="button"
            :class="{ selected: journey.preferences.walkingTime === option.value }"
            :aria-pressed="journey.preferences.walkingTime === option.value"
            @click="journey.preferences.walkingTime = option.value"
          >
            {{ option.label }}
          </button>
        </div>
      </section>

      <section class="preference-card surroundings-card">
        <div class="section-heading">
          <span class="section-icon"><LeafIcon /></span>
          <div>
            <h2>How would you like your surroundings to feel?</h2>
            <p class="helper">
              Adjust the sliders below to choose the level of tree cover and shade you’d like.
            </p>
          </div>
        </div>
        <div class="slider-field">
          <div class="slider-heading">
            <label for="canopy">Tree canopy</label
            ><button
              type="button"
              class="info-button"
              aria-label="About tree canopy"
              :aria-expanded="activeInfo === 'canopy'"
              @click="activeInfo = activeInfo === 'canopy' ? null : 'canopy'"
            >
              <ElIcon><InfoFilled /></ElIcon>
            </button>
          </div>
          <p class="helper">More trees, more canopy, or a more open route.</p>
          <input
            id="canopy"
            type="range"
            min="0"
            max="100"
            step="5"
            :value="journey.preferences.canopy ?? 50"
            :aria-valuetext="
              journey.preferences.canopy === null
                ? 'No preference set'
                : `${journey.preferences.canopy}% tree canopy preference`
            "
            :style="{ '--range-value': `${journey.preferences.canopy ?? 50}%` }"
            @input="setSlider('canopy', $event)"
          />
          <div class="range-labels"><span>Open space</span><span>Dense canopy</span></div>
          <button
            v-if="journey.preferences.canopy !== null"
            type="button"
            class="reset-preference"
            @click="journey.preferences.canopy = null"
          >
            Clear canopy preference
          </button>
        </div>
        <div class="slider-field">
          <div class="slider-heading">
            <label for="shade">Shade & thermal comfort</label
            ><button
              type="button"
              class="info-button"
              aria-label="About shade and thermal comfort"
              :aria-expanded="activeInfo === 'shade'"
              @click="activeInfo = activeInfo === 'shade' ? null : 'shade'"
            >
              <ElIcon><InfoFilled /></ElIcon>
            </button>
          </div>
          <p class="helper">Prefer sunshine or somewhere cooler and shaded?</p>
          <input
            id="shade"
            type="range"
            min="0"
            max="100"
            step="5"
            :value="journey.preferences.shade ?? 50"
            :aria-valuetext="
              journey.preferences.shade === null
                ? 'No preference set'
                : `${journey.preferences.shade}% shade preference`
            "
            :style="{ '--range-value': `${journey.preferences.shade ?? 50}%` }"
            @input="setSlider('shade', $event)"
          />
          <div class="range-labels"><span>Sunny & open</span><span>Cool & shaded</span></div>
          <button
            v-if="journey.preferences.shade !== null"
            type="button"
            class="reset-preference"
            @click="journey.preferences.shade = null"
          >
            Clear shade preference
          </button>
        </div>
      </section>

      <section class="preference-card easier-card">
        <div class="section-heading">
          <span class="section-icon"
            ><ElIcon><Headset /></ElIcon
          ></span>
          <div>
            <h2>Make the journey easier</h2>
            <p class="helper">Let us know what kind of surroundings would feel best for you.</p>
          </div>
        </div>
        <fieldset>
          <legend>Noise level</legend>
          <div class="pills">
            <button
              v-for="option in noiseOptions"
              :key="option.label"
              type="button"
              :class="{ selected: journey.preferences.noise === option.value }"
              :aria-pressed="journey.preferences.noise === option.value"
              @click="journey.preferences.noise = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </fieldset>
        <fieldset>
          <legend>Allergy preference</legend>
          <p class="helper">Would you prefer to avoid high-pollen areas?</p>
          <div class="pills">
            <button
              v-for="option in allergyOptions"
              :key="option.label"
              type="button"
              :class="{ selected: journey.preferences.allergy === option.value }"
              :aria-pressed="journey.preferences.allergy === option.value"
              @click="journey.preferences.allergy = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </fieldset>
      </section>

      <p v-if="journey.error" class="form-error" role="alert">{{ journey.error }}</p>
      <button class="primary-button home-cta" type="submit" :disabled="submitting || locating">
        <span v-if="submitting" class="loading-ring" aria-hidden="true" />{{
          submitting ? 'Finding your greener route…' : 'Find my greener route →'
        }}
      </button>
      <p v-if="submitting" class="calculation-note" role="status">
        Finding nearby areas and matching a route to your preferences.
      </p>
    </form>
    <footer class="home-footer"><span /><LeafIcon />Small changes. A bigger impact.<span /></footer>
  </main>
  <PreferenceInfo :active-info="activeInfo" @close="activeInfo = null" />
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
.preferences-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 16px;
  padding: 18px;
  background: var(--tg-green-100);
}
h2 {
  font-size: 1rem;
  line-height: 1.35;
  margin: 0;
  font-weight: 750;
  letter-spacing: -0.025em;
}
.preferences-banner p {
  font-size: 0.82rem;
  line-height: 1.45;
  color: var(--tg-muted);
  margin: 2px 0 0;
}
.preferences-banner .text-button {
  margin-left: auto;
  flex-shrink: 0;
  font-size: 0.8rem;
}
.section-icon {
  display: grid;
  place-items: center;
  flex: 0 0 34px;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--tg-green-50);
  color: var(--tg-green-700);
}
.section-icon svg {
  width: 18px;
  height: 18px;
}
.preferences-banner .section-icon {
  background: white;
  width: 42px;
  height: 42px;
  flex-basis: 42px;
}
.summary-strip {
  min-height: 45px;
  display: flex;
  align-items: center;
  padding: 10px 0 13px;
}
.summary-strip p {
  font-size: 0.82rem;
  font-style: italic;
  color: var(--tg-muted);
  margin: 0;
}
.preference-card {
  background: white;
  border: 1px solid var(--tg-border);
  border-radius: 18px;
  padding: 23px;
  margin-bottom: 18px;
  box-shadow: 0 2px 5px #164e2903;
}
.helper {
  font-size: 0.82rem;
  line-height: 1.45;
  color: var(--tg-muted);
  margin: 3px 0 0;
}
.location-card > .helper {
  max-width: 580px;
  margin-bottom: 17px;
}
.location-button {
  display: flex;
  gap: 7px;
  align-items: center;
  padding: 12px 0;
  min-height: 44px;
  border: none;
  background: none;
  color: var(--tg-green-700);
  font-weight: 700;
  font-size: 0.84rem;
  cursor: pointer;
}
.field-caption {
  color: var(--tg-muted);
  font-size: 0.69rem;
  font-weight: 800;
  text-transform: uppercase;
  margin: 2px 0 8px;
}
.pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.pills button {
  border: 1px solid var(--tg-border);
  border-radius: 24px;
  padding: 8px 13px;
  min-height: 40px;
  background: white;
  color: var(--tg-text);
  font-size: 0.8rem;
  font-weight: 650;
  cursor: pointer;
}
.pills button:hover {
  background: var(--tg-green-50);
  border-color: var(--tg-green-500);
}
.pills button.selected {
  color: white;
  background: var(--tg-green-800);
  border-color: var(--tg-green-800);
}
.coverage-notice {
  display: flex;
  align-items: start;
  gap: 8px;
  margin: 16px 0 0;
}
.coverage-notice .el-icon {
  margin-top: 4px;
  flex-shrink: 0;
}
.section-heading {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 17px;
}
.slider-field + .slider-field {
  margin-top: 21px;
}
.slider-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 30px;
}
.slider-heading label,
legend {
  font-weight: 700;
  font-size: 0.88rem;
}
.info-button {
  background: none;
  border: 0;
  color: var(--tg-muted);
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  margin: -4px -8px;
  cursor: pointer;
}
input[type='range'] {
  appearance: none;
  width: 100%;
  height: 26px;
  background: transparent;
  cursor: pointer;
  margin: 12px 0 0;
}
input[type='range']::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: 6px;
  background: linear-gradient(
    to right,
    var(--tg-green-700) var(--range-value),
    var(--tg-border) var(--range-value)
  );
}
input[type='range']::-webkit-slider-thumb {
  appearance: none;
  background: var(--tg-green-700);
  width: 18px;
  height: 18px;
  border: 3px solid white;
  border-radius: 50%;
  margin-top: -6px;
  box-shadow: 0 0 0 1px var(--tg-green-700);
}
input[type='range']::-moz-range-track {
  height: 6px;
  border-radius: 6px;
  background: var(--tg-border);
}
input[type='range']::-moz-range-progress {
  background: var(--tg-green-700);
  height: 6px;
}
input[type='range']::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--tg-green-700);
  border: 2px solid white;
}
.range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.72rem;
  color: var(--tg-muted);
}
.reset-preference {
  border: 0;
  background: none;
  color: var(--tg-green-700);
  text-decoration: underline;
  padding: 8px 0 0;
  font-size: 0.7rem;
  cursor: pointer;
}
fieldset {
  border: 0;
  padding: 0;
  margin: 0;
  min-width: 0;
}
fieldset + fieldset {
  border-top: 1px solid var(--tg-border);
  margin-top: 16px;
  padding-top: 15px;
}
legend {
  float: left;
  width: 100%;
  margin-bottom: 5px;
}
fieldset .helper {
  clear: both;
  margin-bottom: 9px;
}
fieldset .pills {
  clear: both;
}
.home-cta {
  min-height: 54px;
  font-size: 0.98rem;
  border-radius: 13px;
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
.calculation-note {
  font-size: 0.8rem;
  color: var(--tg-muted);
  text-align: center;
}
.loading-ring {
  width: 17px;
  height: 17px;
  border-radius: 50%;
  border: 2px solid #ffffff66;
  border-top-color: white;
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (min-width: 1000px) {
  .hero-copy {
    padding-top: 40px;
  }
  .home-form {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px;
  }
  .preferences-banner,
  .summary-strip,
  .location-card,
  .time-card,
  .home-cta,
  .home-form > .form-error,
  .calculation-note {
    grid-column: 1 / -1;
  }
  .preference-card {
    margin: 0;
  }
  .summary-strip {
    margin: -12px 0 -10px;
  }
  .preferences-banner {
    padding: 18px 22px;
  }
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
  .preference-card {
    padding: 18px 16px;
    border-radius: 16px;
    margin-bottom: 15px;
  }
  .preferences-banner {
    gap: 9px;
    padding: 14px 12px;
    flex-wrap: wrap;
  }
  .preferences-banner > div {
    flex: 1;
    min-width: 180px;
  }
  .preferences-banner .text-button {
    margin-left: 51px;
    padding: 0;
    min-height: 30px;
  }
  h2 {
    font-size: 0.94rem;
  }
  .helper {
    font-size: 0.78rem;
  }
  .pills {
    gap: 7px;
  }
  .pills button {
    min-height: 44px;
    padding: 8px 12px;
    font-size: 0.76rem;
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
