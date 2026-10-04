<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Clock, Headset, Location as LocationIcon, Warning } from '@element-plus/icons-vue'
import SproutTree from '@/components/sprout/SproutTree.vue'
import LocationSearch from '@/components/LocationSearch.vue'
import GoogleMapCanvas from '@/components/GoogleMapCanvas.vue'
import { useJourneyStore } from '@/stores/journey'
import { useSproutStore } from '@/stores/sprout'
import { useAccessibilityStore } from '@/stores/accessibility'
import { CBD_BOUNDS, CBD_CENTER, CBD_PRECINCT_ID, isWithinCbd } from '@/constants/cbd'
import { getPrecinctZones } from '@/services/discovery.service'
import { getCbdWeather } from '@/services/weather.service'
import {
  AUTO_PRESET_NOTE,
  CANOPY_OPTIONS,
  DEFAULT_MAP_REPLY,
  MOOD_OPTIONS,
  OUTSIDE_CBD_REPLY,
  THERMAL_OPTIONS,
  allergyReply,
  canopyFromSlider,
  canopyReply,
  greeting,
  moodReply,
  noiseReply,
  placeChosenReply,
  routeExplanation,
  temperaturePrompt,
  thermalFromSlider,
  thermalReply,
  type Mood,
} from '@/data/sproutMessages'
import type { Preferences } from '@/types/personalisation'
import type { Precinct, TreeZone, RoutePlace } from '@/types/discovery'
import type { SproutStep } from '@/stores/sprout'

const STEP_LABELS: Record<SproutStep, string> = {
  greeting: 'Greeting',
  feel: 'Feel',
  canopy: 'Canopy',
  shade: 'Shade',
  journey: 'Journey',
  location: 'Location',
  route: 'Route',
}

const journey = useJourneyStore()
const sprout = useSproutStore()
const accessibility = useAccessibilityStore()
const router = useRouter()

const zones = ref<TreeZone[]>([])
const zonesError = ref('')
const temperature = ref<number | null>(null)
const temperatureAvailable = ref(false)
const locating = ref(false)
const locationError = ref('')
const growing = ref(false)
const growError = ref('')

const cbdPrecinct = computed<Precinct[]>(() =>
  journey.precincts.filter((p) => p.id === CBD_PRECINCT_ID),
)

const landmarks: { label: string; coordinates: { lat: number; lng: number } }[] = [
  { label: 'Flinders Street Station', coordinates: { lat: -37.8183, lng: 144.9671 } },
  { label: 'State Library', coordinates: { lat: -37.8099, lng: 144.9656 } },
  { label: 'Melbourne Central', coordinates: { lat: -37.8103, lng: 144.9628 } },
]

const times: { label: string; value: Preferences['walkingTime'] }[] = [
  { label: '5 min', value: 5 },
  { label: '10 min', value: 10 },
  { label: '15 min', value: 15 },
  { label: '20+ min', value: 20 },
]
const noiseOptions: { label: string; value: Preferences['noise'] }[] = [
  { label: 'Quieter', value: 'quiet' },
  { label: 'No preference', value: null },
  { label: 'Lively', value: 'lively' },
]
const allergyOptions: { label: string; value: Preferences['allergy'] }[] = [
  { label: 'Avoid high pollen', value: 'avoid' },
  { label: 'No preference', value: null },
]

const canopyChoice = computed(() => canopyFromSlider(journey.preferences.canopy))
const thermalChoice = computed(() => thermalFromSlider(journey.preferences.shade))

async function loadZones() {
  zonesError.value = ''
  try {
    // The "melbourne" precinct is the full municipal area; CBD_BOUNDS trims
    // it to the Hoddle Grid a user actually recognises as "the CBD".
    const precinctZones = await getPrecinctZones(CBD_PRECINCT_ID)
    zones.value = precinctZones.filter((zone) => isWithinCbd(zone.center))
  } catch {
    zonesError.value = 'The CBD map could not be loaded.'
  }
}

async function loadWeather() {
  try {
    const result = await getCbdWeather()
    temperature.value = result.temperatureCelsius
    temperatureAvailable.value = result.available
  } catch {
    temperatureAvailable.value = false
  }
}

onMounted(() => {
  journey.initialize()
  loadZones()
  loadWeather()
})

/** Sprout's speech bubble: one contextual line per step, per AC. */
const sproutLine = computed(() => {
  switch (sprout.step) {
    case 'feel':
      return sprout.mood ? moodReply(sprout.mood) : 'How are you feeling right now?'
    case 'canopy': {
      const base = canopyChoice.value
        ? canopyReply(canopyChoice.value)
        : 'How much leafy cover would you like overhead?'
      // US5.2: "when they move to Step 2... Sprout says it picked the
      // calmest options and they can change anything" - the note belongs
      // here, not on the mood step itself.
      return sprout.calmPresetApplied ? `${base} ${AUTO_PRESET_NOTE}` : base
    }
    case 'shade':
      return thermalChoice.value ? thermalReply(thermalChoice.value) : temperaturePrompt(temperature.value)
    case 'journey': {
      const noise = noiseReply(journey.preferences.noise)
      const allergy = allergyReply(journey.preferences.allergy)
      return allergy ?? noise ?? 'Let’s make the walk easy on you.'
    }
    case 'location':
      if (locationError.value) return OUTSIDE_CBD_REPLY
      return journey.startLocation ? placeChosenReply(journey.startLocation.label) : DEFAULT_MAP_REPLY
    case 'route':
      return journey.route ? routeExplanation(journey.route) : 'Growing your route…'
    default:
      return ''
  }
})

/** Sprout's face, mirroring the prototype's per-step expression logic. */
const sproutFace = computed(() => {
  switch (sprout.step) {
    case 'feel':
      return sprout.mood === 'tense' || sprout.mood === 'stressed' || sprout.mood === 'overwhelmed'
        ? 'concerned'
        : 'happy'
    case 'canopy':
      return canopyChoice.value === 'dense' ? 'excited' : 'happy'
    case 'shade':
      if (thermalChoice.value === 'sunny') return 'thirsty'
      if (thermalChoice.value === 'cool') return 'calm'
      return 'happy'
    case 'location':
      if (locationError.value) return 'concerned'
      return journey.startLocation ? 'excited' : 'happy'
    case 'route':
      return journey.route ? 'excited' : 'happy'
    default:
      return 'happy'
  }
})

function pickMood(value: Mood) {
  sprout.pickMood(value)
}
function pickCanopy(sliderValue: number) {
  journey.preferences.canopy = sliderValue
}
function pickThermal(sliderValue: number) {
  journey.preferences.shade = sliderValue
}
function setOrigin(value: RoutePlace | null) {
  locationError.value = ''
  journey.startLocation = value
}
function chooseLandmark(place: (typeof landmarks)[number]) {
  if (!isWithinCbd(place.coordinates)) return
  setOrigin({ id: place.label, label: place.label, coordinates: place.coordinates })
}
async function useMyLocation() {
  locating.value = true
  locationError.value = ''
  try {
    await journey.useCurrentLocation()
    if (journey.startLocation && !isWithinCbd(journey.startLocation.coordinates)) {
      journey.startLocation = null
      locationError.value = 'Southbank is outside the CBD, so I don’t know its trees yet. Pick a starting point inside the dashed area.'
    }
  } catch (e) {
    locationError.value = e instanceof Error ? e.message : 'Location is unavailable.'
  } finally {
    locating.value = false
  }
}
async function growRoute() {
  if (!journey.startLocation) return
  growing.value = true
  growError.value = ''
  try {
    if (await journey.findGreenerRoute()) sprout.next()
    else growError.value = journey.error ?? 'The route could not be calculated.'
  } finally {
    growing.value = false
  }
}
function changeAnswers() {
  sprout.goToStep(sprout.progress.some((p) => p.id === 'feel' && p.reached) ? 'feel' : 'location')
}
function goToWalk() {
  router.push('/explore')
}

watch(
  () => [locationError.value, zonesError.value, growError.value],
  ([a, b, c]) => {
    const message = a || b || c
    if (message) accessibility.speak(message)
  },
)
</script>

<template>
  <div class="sprout-guide">
    <!-- Greeting (US5.1) -->
    <div v-if="sprout.step === 'greeting'" class="sprout-greeting">
      <SproutTree class="sprout-avatar" :size="140" face="happy" wave />
      <span class="sprout-eyebrow">SPROUT SAYS</span>
      <h1>{{ greeting().title }}</h1>
      <p>{{ greeting().body }}</p>
      <div class="greeting-actions">
        <button type="button" class="primary-button" @click="sprout.beginGuided">
          Hi Sprout, let’s go
        </button>
        <button type="button" class="ghost-button" @click="sprout.skipToMap">Skip to the map</button>
      </div>
    </div>

    <template v-else>
      <nav class="sprout-progress" aria-label="Sprout guided steps">
        <button
          v-for="(item, index) in sprout.progress"
          :key="item.id"
          type="button"
          class="progress-step"
          :class="{ active: item.active, reached: item.reached }"
          :disabled="!item.reached"
          :aria-current="item.active ? 'step' : undefined"
          @click="sprout.goToStep(item.id)"
        >
          <span class="progress-dot">{{ index + 1 }}</span>
          <span class="progress-label">{{ STEP_LABELS[item.id] }}</span>
        </button>
        <button type="button" class="text-button replay" @click="sprout.replayIntro">
          Replay intro
        </button>
      </nav>

      <div class="sprout-bubble" role="status">
        <SproutTree class="sprout-avatar small" :size="64" :face="sproutFace" :canopy="canopyChoice" />
        <p>{{ sproutLine }}</p>
      </div>

      <!-- Step 1: Feel (US5.2) -->
      <section v-if="sprout.step === 'feel'" class="sprout-step">
        <h2>How are you feeling right now?</h2>
        <div class="mood-grid" role="group" aria-label="Current mood">
          <button
            v-for="option in MOOD_OPTIONS"
            :key="option.value"
            type="button"
            class="mood-option"
            :class="{ selected: sprout.mood === option.value }"
            :aria-pressed="sprout.mood === option.value"
            @click="pickMood(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
        <p class="step-note">Optional - you can move on without picking one.</p>
      </section>

      <!-- Step 2: Canopy (US5.3) -->
      <section v-else-if="sprout.step === 'canopy'" class="sprout-step">
        <h2>How much leafy cover would you like overhead?</h2>
        <div class="option-grid" role="group" aria-label="Canopy preference">
          <button
            v-for="option in CANOPY_OPTIONS"
            :key="option.value"
            type="button"
            class="option-card"
            :class="{ selected: canopyChoice === option.value }"
            :aria-pressed="canopyChoice === option.value"
            @click="pickCanopy(option.sliderValue)"
          >
            {{ option.label }}
          </button>
        </div>
      </section>

      <!-- Step 3: Shade & thermal comfort (US5.3) -->
      <section v-else-if="sprout.step === 'shade'" class="sprout-step">
        <div class="step-heading-row">
          <h2>Sun or shade?</h2>
          <span v-if="temperatureAvailable && temperature !== null" class="temp-chip"
            >CBD now · {{ temperature }}°C</span
          >
        </div>
        <div class="option-grid" role="group" aria-label="Shade and thermal comfort">
          <button
            v-for="option in THERMAL_OPTIONS"
            :key="option.value"
            type="button"
            class="option-card"
            :class="{ selected: thermalChoice === option.value }"
            :aria-pressed="thermalChoice === option.value"
            @click="pickThermal(option.sliderValue)"
          >
            {{ option.label }}
          </button>
        </div>
      </section>

      <!-- Step 4: Journey (US5.4) -->
      <section v-else-if="sprout.step === 'journey'" class="sprout-step">
        <h2>Let’s make the journey easier</h2>
        <fieldset>
          <legend><ElIcon><Clock /></ElIcon> How much time do you have?</legend>
          <div class="pills">
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
        </fieldset>
        <fieldset>
          <legend><ElIcon><Headset /></ElIcon> Noise level</legend>
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
          <legend>Allergies</legend>
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

      <!-- Step 5: CBD map and start point (US5.5) -->
      <section v-else-if="sprout.step === 'location'" class="sprout-step location-step">
        <h2>Where are you starting from?</h2>
        <p class="step-note">I only know the trees in Melbourne’s CBD for now.</p>
        <LocationSearch
          :model-value="journey.startLocation"
          :precincts="cbdPrecinct"
          :invalid="!!locationError"
          @update:model-value="setOrigin"
        />
        <div class="pills landmark-pills">
          <button
            v-for="landmark in landmarks"
            :key="landmark.label"
            type="button"
            :class="{ selected: journey.startLocation?.label === landmark.label }"
            @click="chooseLandmark(landmark)"
          >
            {{ landmark.label }}
          </button>
        </div>
        <button type="button" class="location-button" :disabled="locating" @click="useMyLocation">
          <ElIcon><LocationIcon /></ElIcon>{{ locating ? 'Finding your location…' : 'Use my location' }}
        </button>
        <p v-if="locationError" class="notice outside-cbd" role="alert">
          <ElIcon><Warning /></ElIcon>{{ locationError }}
        </p>
        <p v-if="zonesError" class="form-error" role="alert">{{ zonesError }}</p>
        <div class="cbd-map">
          <GoogleMapCanvas
            :center="CBD_CENTER"
            :trees="[]"
            :zones="zones"
            :directions-open="false"
            :route-options="[]"
            :origin="journey.startLocation?.coordinates"
            :cbd-bounds="CBD_BOUNDS"
            :auto-center="false"
          />
        </div>
        <button
          type="button"
          class="primary-button grow-button"
          :disabled="!journey.startLocation || growing"
          @click="growRoute"
        >
          <span v-if="growing" class="loading-ring" aria-hidden="true" />{{
            !journey.startLocation
              ? 'Choose a start point first'
              : growing
                ? 'Growing your route…'
                : 'Grow my route'
          }}
        </button>
        <p v-if="growError" class="form-error" role="alert">{{ growError }}</p>
      </section>

      <!-- Step 6: Route and explanation (US5.6) -->
      <section v-else-if="sprout.step === 'route'" class="sprout-step">
        <template v-if="journey.route">
          <h2>Your greener route</h2>
          <div class="route-facts">
            <div class="fact"><span>Walk time</span><strong>{{ journey.route.durationMinutes }} min</strong></div>
            <div class="fact"><span>Distance</span><strong>{{ journey.route.distanceKm.toFixed(1) }} km</strong></div>
            <div v-if="journey.route.metrics?.canopy != null" class="fact">
              <span>Tree-dense zones</span><strong>{{ Math.round(journey.route.metrics.canopy) }}%</strong>
            </div>
          </div>
          <div v-if="journey.summary.length" class="preference-chips">
            <span v-for="chip in journey.summary" :key="chip" class="preference-chip">{{ chip }}</span>
          </div>
          <div class="route-actions">
            <button type="button" class="ghost-button" @click="changeAnswers">Change answers</button>
            <button type="button" class="primary-button" @click="goToWalk">See full route →</button>
          </div>
        </template>
        <template v-else>
          <p v-if="growError" class="form-error" role="alert">{{ growError }}</p>
          <button type="button" class="primary-button" @click="growRoute">Try again</button>
        </template>
      </section>

      <div v-if="sprout.step !== 'location' && sprout.step !== 'route'" class="step-nav">
        <button type="button" class="ghost-button" @click="sprout.back">Back</button>
        <button type="button" class="primary-button" @click="sprout.next">Next</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.sprout-guide {
  background: white;
  border: 1px solid var(--tg-border);
  border-radius: 18px;
  padding: 24px;
  margin-bottom: 18px;
}
.sprout-greeting {
  text-align: center;
  padding: 20px 10px;
}
.sprout-avatar {
  margin: 0 auto 4px;
}
.sprout-avatar.small {
  flex-shrink: 0;
}
.sprout-eyebrow {
  display: block;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: var(--tg-green-700);
}
.sprout-greeting h1 {
  margin: 6px 0;
  font:
    bold 1.6rem/1.1 Georgia,
    serif;
  color: var(--tg-green-950);
}
.sprout-greeting p {
  max-width: 420px;
  margin: 0 auto;
  color: var(--tg-muted);
}
.greeting-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 18px;
  flex-wrap: wrap;
}
.sprout-progress {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.progress-step {
  display: flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--tg-muted);
  cursor: not-allowed;
}
.progress-step.reached {
  cursor: pointer;
  color: var(--tg-text);
}
.progress-step.active {
  background: var(--tg-green-800);
  color: white;
}
.progress-dot {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--tg-green-50);
  color: var(--tg-green-700);
  font-size: 0.68rem;
}
.progress-step.active .progress-dot {
  background: white;
  color: var(--tg-green-800);
}
.replay {
  margin-left: auto;
}
.sprout-bubble {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: var(--tg-green-50);
  border: 1px solid var(--tg-green-100);
  border-radius: 14px;
  padding: 12px 14px;
  margin-bottom: 18px;
}
.sprout-bubble p {
  margin: 4px 0 0;
  font-size: 0.86rem;
  line-height: 1.45;
}
.sprout-step h2 {
  font-size: 1.1rem;
  margin: 0 0 12px;
}
.step-note {
  font-size: 0.8rem;
  color: var(--tg-muted);
  margin: 6px 0 0;
}
.mood-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}
.mood-option,
.option-card {
  border: 2px solid var(--tg-border);
  border-radius: 14px;
  padding: 14px 8px;
  background: white;
  font-size: 0.8rem;
  font-weight: 650;
  cursor: pointer;
  text-align: center;
}
.option-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.mood-option.selected,
.option-card.selected {
  border-color: var(--tg-green-700);
  background: var(--tg-green-50);
  color: var(--tg-green-900);
}
.step-heading-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.step-heading-row h2 {
  margin: 0;
}
.temp-chip {
  font-size: 0.72rem;
  font-weight: 700;
  color: #6b4a1f;
  background: #f7ead2;
  border-radius: 999px;
  padding: 3px 10px;
}
fieldset {
  border: 0;
  padding: 0;
  margin: 0 0 18px;
}
fieldset legend {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 0.88rem;
  margin-bottom: 8px;
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
  font-size: 0.8rem;
  font-weight: 650;
  cursor: pointer;
}
.pills button.selected {
  color: white;
  background: var(--tg-green-800);
  border-color: var(--tg-green-800);
}
.landmark-pills {
  margin: 10px 0;
}
.location-button {
  display: flex;
  gap: 7px;
  align-items: center;
  padding: 10px 0;
  border: none;
  background: none;
  color: var(--tg-green-700);
  font-weight: 700;
  font-size: 0.84rem;
  cursor: pointer;
}
.outside-cbd {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  color: #8a4a12;
}
.cbd-map {
  position: relative;
  height: 320px;
  border-radius: 14px;
  overflow: hidden;
  margin: 14px 0;
  border: 1px solid var(--tg-border);
}
.grow-button {
  width: 100%;
  min-height: 52px;
}
.route-facts {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.fact {
  flex: 1;
  min-width: 110px;
  border: 1px solid var(--tg-border);
  border-radius: 12px;
  padding: 10px 14px;
}
.fact span {
  display: block;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--tg-muted);
}
.fact strong {
  font-size: 1.1rem;
}
.preference-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.preference-chip {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--tg-green-900);
  background: var(--tg-green-100);
  border-radius: 999px;
  padding: 5px 11px;
}
.route-actions,
.step-nav {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 18px;
}
.primary-button {
  background: var(--tg-green-800);
  color: white;
  border: none;
  border-radius: 999px;
  padding: 13px 22px;
  font-weight: 700;
  font-size: 0.88rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
}
.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.ghost-button {
  background: white;
  color: var(--tg-green-800);
  border: 1.5px solid var(--tg-green-800);
  border-radius: 999px;
  padding: 13px 22px;
  font-weight: 700;
  font-size: 0.88rem;
  cursor: pointer;
}
.text-button {
  background: none;
  border: none;
  color: var(--tg-green-700);
  font-weight: 700;
  font-size: 0.78rem;
  cursor: pointer;
}
.form-error {
  color: #b44235;
  font-size: 0.82rem;
}
.loading-ring {
  width: 15px;
  height: 15px;
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
@media (max-width: 600px) {
  .mood-grid {
    grid-template-columns: repeat(auto-fit, minmax(72px, 1fr));
  }
  .option-grid {
    grid-template-columns: 1fr;
  }
}
</style>
