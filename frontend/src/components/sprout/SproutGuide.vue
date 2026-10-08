<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Clock, Headset, Location as LocationIcon, Warning } from '@element-plus/icons-vue'
import SproutTree from '@/components/sprout/SproutTree.vue'
import HillsBackdrop from '@/components/sprout/HillsBackdrop.vue'
import LocationSearch from '@/components/LocationSearch.vue'
import GoogleMapCanvas from '@/components/GoogleMapCanvas.vue'
import { useJourneyStore } from '@/stores/journey'
import { useSproutStore } from '@/stores/sprout'
import { useAccessibilityStore } from '@/stores/accessibility'
import { MELBOURNE_CENTER, loadAllZones } from '@/constants/zones'
import { getCbdWeather } from '@/services/weather.service'
import {
  AUTO_PRESET_NOTE,
  CANOPY_OPTIONS,
  DEFAULT_MAP_REPLY,
  MOOD_OPTIONS,
  ROUTE_FAILURE_BUBBLE,
  THERMAL_OPTIONS,
  allergyReply,
  canopyFromSlider,
  canopyReply,
  greeting,
  moodReply,
  noiseReply,
  placeChosenReply,
  routeFailureMessage,
  temperaturePrompt,
  thermalFromSlider,
  thermalReply,
  type Mood,
} from '@/data/sproutMessages'
import type { Preferences } from '@/types/personalisation'
import type { RouteOption, TreeZone, RoutePlace } from '@/types/discovery'
import { STEP_ORDER, type SproutStep } from '@/stores/sprout'

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
const zoneCount = ref(0)
const zonesError = ref('')
const temperature = ref<number | null>(null)
const temperatureAvailable = ref(false)
const locating = ref(false)
const locationError = ref('')
const growing = ref(false)
const growError = ref('')

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

const currentMood = computed(() => MOOD_OPTIONS.find((o) => o.value === sprout.mood) ?? null)

/** Steps 5 and 6 use the full-bleed map layout from the prototype. */
const isMapStep = computed(() => sprout.step === 'location' || sprout.step === 'route')

/** Button label for the step after this one, e.g. "Next: canopy". */
const nextStepLabel = computed(() => {
  const target = STEP_ORDER[STEP_ORDER.indexOf(sprout.step) + 1]
  return target ? STEP_LABELS[target] : ''
})

/** US5.4: the last preference step hands off with "Show me the map". */
const nextButtonLabel = computed(() =>
  sprout.step === 'journey' ? 'Show me the map' : `Next: ${nextStepLabel.value.toLowerCase()}`,
)

/** US5.3: the number of trees drawn beside Sprout follows the canopy choice. */
const companionTreeCount = computed(
  () => CANOPY_OPTIONS.find((o) => o.value === canopyChoice.value)?.treeCount ?? 0,
)

/** Sky tint behind Sprout on the Shade step, following the sun/shade choice. */
const stageSkyClass = computed(() =>
  sprout.step === 'shade' && thermalChoice.value ? `sky-${thermalChoice.value}` : '',
)

async function loadZones() {
  zonesError.value = ''
  try {
    // Citywide, not CBD-only any more - every precinct's zones, merged.
    const result = await loadAllZones()
    zones.value = result.zones
    zoneCount.value = result.zoneCount
  } catch {
    zonesError.value = 'The map could not be loaded.'
  }
}

/** Adapts Sprout's route to the shape GoogleMapCanvas's routeOptions expects. */
const mapRouteOptions = computed<RouteOption[]>(() => {
  const route = journey.sproutRoute
  if (sprout.step !== 'route' || !route) return []
  return [
    {
      id: 'personalised',
      label: route.destination.label,
      durationMinutes: route.durationMinutes,
      distanceKm: route.distanceMeters / 1000,
      treeCount: route.destination.treeCount,
      encodedPolyline: route.encodedPolyline,
    },
  ]
})

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
      if (locationError.value) return locationError.value
      return journey.startLocation ? placeChosenReply(journey.startLocation.label) : DEFAULT_MAP_REPLY
    case 'route':
      if (journey.sproutRoute) {
        // Sprout's own fixed-template sentence (backend/app/services/sprout.py) -
        // never generated here, so it can never claim a match the route didn't make.
        return journey.sproutRoute.explanation ?? `Here's a walk to ${journey.sproutRoute.destination.label}.`
      }
      return growError.value ? ROUTE_FAILURE_BUBBLE : 'Growing your route…'
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
      if (journey.sproutRoute) return 'excited'
      return growError.value ? 'concerned' : 'happy'
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
  setOrigin({ id: place.label, label: place.label, coordinates: place.coordinates })
}
async function useMyLocation() {
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
async function growRoute() {
  if (!journey.startLocation) return
  growing.value = true
  growError.value = ''
  try {
    const ok = await journey.growSproutRoute()
    if (!ok) growError.value = routeFailureMessage(journey.sproutRouteError)
    // US5.6: a failed request still shows Sprout's plain message and a Try
    // again button (the Route step's own failure view), not a dead end on
    // the Location step.
    sprout.next()
  } finally {
    growing.value = false
  }
}
function changeAnswers() {
  sprout.goToStep(sprout.progress.some((p) => p.id === 'feel' && p.reached) ? 'feel' : 'location')
}
function startWalk() {
  router.push('/walk')
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
  <div class="sprout-page">
    <!-- Greeting (US5.1) -->
    <div v-if="sprout.step === 'greeting'" class="sprout-greeting">
      <svg class="sun sun-corner" viewBox="0 0 60 60" aria-hidden="true">
        <circle cx="30" cy="30" r="13" fill="#f4c04f" />
        <path
          d="M30 6v7M30 47v7M6 30h7M47 30h7M13 13l5 5M42 42l5 5M13 47l5-5M42 18l5-5"
          stroke="#f4c04f"
          stroke-width="2.5"
          stroke-linecap="round"
        />
      </svg>
      <div class="greeting-bubble">
        <span class="eyebrow">SPROUT SAYS</span>
        <h1>{{ greeting().title }}</h1>
        <p>{{ greeting().body }}</p>
      </div>
      <SproutTree class="sprout-avatar" :size="170" face="happy" wave />
      <div class="greeting-actions">
        <button type="button" class="primary-button" @click="sprout.beginGuided">
          Hi Sprout, let’s go
        </button>
        <button type="button" class="ghost-button" @click="sprout.skipToMap">Skip to the map</button>
      </div>
      <HillsBackdrop />
    </div>

    <template v-else>
      <nav class="sprout-progress" aria-label="Sprout guided steps">
        <button
          v-for="(item, index) in sprout.progress"
          :key="item.id"
          type="button"
          class="progress-step"
          :class="{
            active: item.active,
            reached: item.reached,
            done: item.reached && !item.active && index < sprout.progress.findIndex((p) => p.active),
          }"
          :disabled="!item.reached"
          :aria-current="item.active ? 'step' : undefined"
          @click="sprout.goToStep(item.id)"
        >
          <span class="progress-dot">
            <template v-if="index < sprout.progress.findIndex((p) => p.active)">✓</template>
            <template v-else>{{ index + 1 }}</template>
          </span>
          <span class="progress-label">{{ STEP_LABELS[item.id] }}</span>
        </button>
        <button type="button" class="text-button replay" @click="sprout.replayIntro">Replay intro</button>
      </nav>

      <!-- Steps 5 and 6 are a full-bleed map with floating cards, as in the prototype -->
      <div v-if="isMapStep" class="sprout-body map-mode">
        <div class="map-stage">
          <div class="cbd-map">
            <GoogleMapCanvas
              :center="MELBOURNE_CENTER"
              :trees="[]"
              :zones="zones"
              :directions-open="sprout.step === 'route'"
              :route-options="mapRouteOptions"
              :origin="journey.startLocation?.coordinates"
              :destination="sprout.step === 'route' ? journey.destination?.coordinates : undefined"
              :auto-center="false"
            />
          </div>
          <span class="map-label">TOUCHGRASS TREE-DENSE AREAS</span>
          <div class="map-legend" aria-label="Map legend">
            <span class="legend-title">TREE DENSITY · {{ zoneCount }} ZONES</span>
            <span><i class="swatch high" />High</span>
            <span><i class="swatch medium" />Medium</span>
            <span><i class="swatch low" />Low</span>
          </div>
        </div>

        <aside class="float-card" :class="{ 'route-card': sprout.step === 'route' }">
          <!-- Step 5: location -->
          <template v-if="sprout.step === 'location'">
            <span class="eyebrow">STEP 5 · YOUR LOCATION</span>
            <h2>Where are you starting from?</h2>
            <LocationSearch
              :model-value="journey.startLocation"
              :precincts="journey.precincts"
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
            <p v-if="locationError" class="notice location-notice" role="alert">
              <ElIcon><Warning /></ElIcon>{{ locationError }}
            </p>
            <p v-if="zonesError" class="form-error" role="alert">{{ zonesError }}</p>
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
          </template>

          <!-- Step 6: route -->
          <template v-else-if="sprout.step === 'route'">
            <template v-if="journey.sproutRoute">
              <span class="eyebrow">YOUR GREENER ROUTE</span>
              <h2>A leafy, calm walk to {{ journey.sproutRoute.destination.label }}</h2>
              <div class="route-facts">
                <div class="fact">
                  <span>WALK TIME</span>
                  <strong
                    >{{ journey.sproutRoute.durationMinutes }} min ·
                    {{ (journey.sproutRoute.distanceMeters / 1000).toFixed(1) }} km</strong
                  >
                </div>
                <div class="fact">
                  <span>THROUGH TREE-DENSE ZONES</span>
                  <strong>{{ Math.round(journey.sproutRoute.denseZoneShare * 100) }}%</strong>
                </div>
              </div>
              <div v-if="journey.sproutRoute.summaryChips.length" class="preference-chips">
                <span v-for="chip in journey.sproutRoute.summaryChips" :key="chip" class="preference-chip">{{
                  chip
                }}</span>
              </div>
              <p v-if="journey.sproutRoute.message" class="route-note" role="status">
                {{ journey.sproutRoute.message }}
              </p>
              <div class="route-actions">
                <button type="button" class="primary-button" @click="startWalk">Start walk</button>
                <button type="button" class="ghost-button" @click="changeAnswers">Change answers</button>
              </div>
              <p class="footnote">Zones from City of Melbourne tree data. Distances approximate.</p>
            </template>
            <template v-else>
              <span class="eyebrow">YOUR GREENER ROUTE</span>
              <p v-if="growError" class="form-error" role="alert">{{ growError }}</p>
              <button type="button" class="primary-button" @click="growRoute">Try again</button>
            </template>
          </template>
        </aside>

        <aside class="bubble-anchor">
          <div class="sprout-bubble" role="status">
            <span class="eyebrow">SPROUT SAYS</span>
            <p>{{ sproutLine }}</p>
          </div>
          <SproutTree :size="96" :face="sproutFace" :canopy="canopyChoice" />
        </aside>
      </div>

      <!-- Steps 1 to 4: two columns, Sprout on the left -->
      <div v-else class="sprout-body">
        <HillsBackdrop />
        <aside class="sprout-stage" :class="stageSkyClass">
          <svg class="stage-sun" viewBox="0 0 60 60" aria-hidden="true">
            <circle cx="30" cy="30" r="13" fill="#f4c04f" />
            <path
              d="M30 6v7M30 47v7M6 30h7M47 30h7M13 13l5 5M42 42l5 5M13 47l5-5M42 18l5-5"
              stroke="#f4c04f"
              stroke-width="2.5"
              stroke-linecap="round"
            />
          </svg>
          <div class="sprout-bubble" role="status">
            <span class="eyebrow">SPROUT SAYS</span>
            <p>{{ sproutLine }}</p>
          </div>
          <div class="stage-figure">
            <div
              v-if="sprout.step === 'canopy' && companionTreeCount"
              class="companion-trees"
              aria-hidden="true"
            >
              <svg v-for="n in companionTreeCount" :key="n" width="34" height="40" viewBox="0 0 60 70">
                <rect x="27" y="44" width="6" height="24" rx="2" fill="#8a5a3b" />
                <circle cx="30" cy="30" r="24" fill="#5fa150" />
              </svg>
            </div>
            <SproutTree class="stage-tree" :size="220" :face="sproutFace" :canopy="canopyChoice" />
          </div>
        </aside>

        <section class="sprout-panel">
          <!-- Step 1: Feel (US5.2) -->
          <section v-if="sprout.step === 'feel'" class="sprout-step">
            <span class="eyebrow">STEP 1 · HOW YOU FEEL</span>
            <h2>First things first. How are you feeling right now?</h2>
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
                <svg width="44" height="44" viewBox="0 0 40 40" aria-hidden="true">
                  <circle cx="20" cy="20" r="18" :fill="option.color" />
                  <circle cx="14" cy="17" r="2.2" fill="#2b2118" />
                  <circle cx="26" cy="17" r="2.2" fill="#2b2118" />
                  <path :d="option.mouth" stroke="#2b2118" stroke-width="2.4" fill="none" stroke-linecap="round" />
                </svg>
                <span>{{ option.label }}</span>
              </button>
            </div>
            <div class="stress-gauge">
              <div class="gauge-head">
                <span>Stress gauge</span>
                <strong>{{ currentMood ? `${currentMood.stress} / 5` : 'Not set' }}</strong>
              </div>
              <div
                class="gauge-track"
                role="meter"
                aria-label="Stress level"
                aria-valuemin="1"
                aria-valuemax="5"
                :aria-valuenow="currentMood?.stress ?? 0"
              >
                <div
                  class="gauge-fill"
                  :style="{
                    width: `${(currentMood?.stress ?? 0) * 20}%`,
                    background: currentMood?.color ?? 'transparent',
                  }"
                />
              </div>
            </div>
            <p class="step-note">Optional - you can move on without picking one.</p>
          </section>

          <!-- Step 2: Canopy (US5.3) -->
          <section v-else-if="sprout.step === 'canopy'" class="sprout-step">
            <span class="eyebrow">STEP 2 · TREE CANOPY</span>
            <h2>How much leafy cover would you like overhead?</h2>
            <p class="step-note lead">Watch my friends appear as you choose.</p>
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
                <span class="option-title">{{ option.label }}</span>
                <span class="option-hint">{{ option.hint }}</span>
                <span class="tree-row" aria-hidden="true">
                  <svg v-for="n in option.treeCount" :key="n" width="18" height="22" viewBox="0 0 60 70">
                    <rect x="27" y="44" width="6" height="24" rx="2" fill="#8a5a3b" />
                    <circle cx="30" cy="30" r="24" fill="#5fa150" />
                  </svg>
                </span>
              </button>
            </div>
          </section>

          <!-- Step 3: Shade & thermal comfort (US5.3) -->
          <section v-else-if="sprout.step === 'shade'" class="sprout-step">
            <span class="eyebrow">STEP 3 · SHADE AND THERMAL COMFORT</span>
            <div class="step-heading-row">
              <h2>{{ temperaturePrompt(temperatureAvailable ? temperature : null) }}</h2>
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
                <span class="option-title">{{ option.label }}</span>
                <span class="option-hint">{{ option.hint }}</span>
              </button>
            </div>
          </section>

          <!-- Step 4: Journey (US5.4) -->
          <section v-else-if="sprout.step === 'journey'" class="sprout-step">
            <span class="eyebrow">STEP 4 · MAKE THE JOURNEY EASIER</span>
            <h2>Last bit. Let’s make the walk easy on you.</h2>
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

          <div class="step-nav">
            <button type="button" class="text-button" @click="sprout.back">Back</button>
            <div class="step-nav-right">
              <button type="button" class="ghost-button" @click="sprout.skipToMap">Skip to map</button>
              <button type="button" class="primary-button" @click="sprout.next">{{ nextButtonLabel }}</button>
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.sprout-page {
  --sp-serif: 'Fraunces', Georgia, serif;
  --sp-sans: 'Figtree', system-ui, sans-serif;
  --sp-cream: #f5f2e8;
  --sp-ink: #1d2a1d;
  --sp-green: #1f5a2c;
  --sp-green-soft: #e4eee4;
  flex: 1;
  display: flex;
  flex-direction: column;
  font-family: var(--sp-sans);
  color: var(--sp-ink);
  background: var(--sp-cream);
}
.eyebrow {
  display: block;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: var(--sp-green);
}
h1,
h2 {
  font-family: var(--sp-serif);
  font-weight: 700;
  color: var(--sp-ink);
  line-height: 1.12;
}

/* Greeting */
.sprout-greeting {
  position: relative;
  overflow: hidden;
  flex: 1;
  min-height: 620px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 40px 20px 150px;
  text-align: center;
}
.sun-corner {
  position: absolute;
  left: 34px;
  top: 36px;
  width: 52px;
  height: 52px;
}
.greeting-bubble {
  position: relative;
  max-width: 460px;
  background: white;
  border: 1.5px solid #e6e1d0;
  border-radius: 24px;
  padding: 18px 26px 20px;
  box-shadow: 0 12px 28px #1d2a1d14;
  margin-bottom: 22px;
}
.greeting-bubble::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: -10px;
  width: 18px;
  height: 18px;
  background: white;
  border-right: 1.5px solid #e6e1d0;
  border-bottom: 1.5px solid #e6e1d0;
  transform: translateX(-50%) rotate(45deg);
}
.greeting-bubble h1 {
  margin: 4px 0 6px;
  font-size: 2.2rem;
}
.greeting-bubble p {
  margin: 0;
  color: #4a5a4a;
  font-size: 0.98rem;
  line-height: 1.5;
}
.sprout-avatar {
  position: relative;
  z-index: 1;
}
.greeting-actions {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 20px;
}

/* Hills, shared by the greeting and the stage */
.hills {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 150px;
  pointer-events: none;
}

/* Stepper */
.sprout-progress {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding: 12px 28px;
  background: white;
  border-bottom: 1px solid #e6e1d0;
}
.progress-step {
  display: flex;
  align-items: center;
  gap: 7px;
  border: none;
  background: transparent;
  border-radius: 999px;
  padding: 6px 12px 6px 6px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #7a8478;
  cursor: not-allowed;
}
.progress-step.reached {
  cursor: pointer;
  color: var(--sp-ink);
}
.progress-step.active {
  background: var(--sp-green);
  color: white;
}
.progress-dot {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #ece8da;
  color: #5d6a5c;
  font-size: 0.72rem;
  font-weight: 700;
}
.progress-step.done .progress-dot {
  background: var(--sp-green);
  color: white;
}
.progress-step.active .progress-dot {
  background: white;
  color: var(--sp-green);
}
.replay {
  margin-left: auto;
}

/* Steps 1 to 4 */
.sprout-body {
  position: relative;
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  min-height: 0;
}
.sprout-stage {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 36px 0;
  min-height: 620px;
}
.stage-sun {
  position: absolute;
  left: 36px;
  top: 34px;
  width: 52px;
  height: 52px;
  z-index: 1;
}
.sprout-bubble {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 380px;
  background: white;
  border: 1.5px solid #e6e1d0;
  border-radius: 22px;
  padding: 16px 20px;
  box-shadow: 0 10px 24px #1d2a1d12;
  margin-left: 40px;
}
.sprout-bubble::after {
  content: '';
  position: absolute;
  left: 60px;
  bottom: -9px;
  width: 16px;
  height: 16px;
  background: white;
  border-right: 1.5px solid #e6e1d0;
  border-bottom: 1.5px solid #e6e1d0;
  transform: rotate(45deg);
}
.sprout-bubble p {
  margin: 4px 0 0;
  font-family: var(--sp-serif);
  font-size: 1.1rem;
  font-weight: 600;
  line-height: 1.35;
  color: var(--sp-ink);
}
.stage-figure {
  position: relative;
  z-index: 1;
  margin-top: auto;
  padding-top: 36px;
  padding-bottom: 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.stage-tree {
  margin: 0;
}
.companion-trees {
  display: flex;
  gap: 6px;
  align-items: flex-end;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 4px;
  min-height: 40px;
}
.sprout-stage.sky-sunny {
  background: #fbf0d4;
}
.sprout-stage.sky-cool {
  background: #e7f1f4;
}
.sprout-panel {
  position: relative;
  z-index: 1;
  min-width: 0;
  padding: 48px 56px 40px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.sprout-step {
  flex: 1;
}
.sprout-step h2 {
  margin: 6px 0 16px;
  font-size: 2rem;
  max-width: 560px;
}
.lead {
  margin: -6px 0 14px;
  font-size: 0.95rem;
}
.step-note {
  font-size: 0.82rem;
  color: #6b766a;
  margin: 8px 0 0;
}
.mood-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}
.mood-option,
.option-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  border: 1.5px solid #e0dbcb;
  border-radius: 16px;
  padding: 16px 8px;
  background: white;
  font-family: var(--sp-sans);
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--sp-ink);
  cursor: pointer;
  text-align: center;
}
.mood-option.selected,
.option-card.selected {
  border-color: var(--sp-green);
  background: var(--sp-green-soft);
  box-shadow: inset 0 0 0 1px var(--sp-green);
}
.option-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.option-card {
  padding: 22px 14px;
  min-height: 140px;
  justify-content: center;
}
.option-title {
  font-weight: 700;
}
.option-hint {
  font-size: 0.78rem;
  font-weight: 500;
  color: #6b766a;
  line-height: 1.35;
}
.tree-row {
  display: flex;
  gap: 2px;
  align-items: flex-end;
  height: 22px;
}
.stress-gauge {
  margin-top: 22px;
}
.gauge-head {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  font-weight: 600;
  color: #6b766a;
  margin-bottom: 6px;
}
.gauge-track {
  height: 8px;
  border-radius: 999px;
  background: #e4e0d2;
  overflow: hidden;
}
.gauge-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 300ms ease;
}
.step-heading-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
  /* Spacing to the option cards below lives here, not on h2's own margin -
     when the chip wraps onto its own line, a child's margin stops reliably
     creating space between flex-wrap lines. */
  margin: 6px 0 20px;
}
.step-heading-row h2 {
  margin: 0;
}
.temp-chip {
  font-size: 0.74rem;
  font-weight: 700;
  color: #6b4a1f;
  background: #f7ead2;
  border-radius: 999px;
  padding: 4px 11px;
  white-space: nowrap;
}
fieldset {
  border: 0;
  padding: 0;
  margin: 0 0 22px;
}
fieldset legend {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 0.92rem;
  margin-bottom: 10px;
}
.pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.pills button {
  border: 1.5px solid #e0dbcb;
  border-radius: 999px;
  padding: 9px 15px;
  min-height: 40px;
  background: white;
  font-family: var(--sp-sans);
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
}
.pills button.selected {
  color: white;
  background: var(--sp-green);
  border-color: var(--sp-green);
}

/* Steps 5 and 6: full-bleed map */
.map-mode {
  position: relative;
  display: block;
  height: calc(100vh - 150px);
  min-height: 640px;
  overflow: hidden;
}
.map-stage {
  position: absolute;
  inset: 0;
}
.cbd-map {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.map-label {
  position: absolute;
  left: 50%;
  top: 14px;
  transform: translateX(-50%);
  z-index: 2;
  background: white;
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: var(--sp-green);
  box-shadow: 0 4px 12px #1d2a1d1a;
  pointer-events: none;
}
.map-legend {
  position: absolute;
  right: 18px;
  bottom: 18px;
  z-index: 2;
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  max-width: 300px;
  background: white;
  border-radius: 14px;
  padding: 10px 14px;
  box-shadow: 0 6px 18px #1d2a1d1f;
  font-size: 0.74rem;
  color: #4a5a4a;
}
.legend-title {
  width: 100%;
  font-size: 0.66rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: var(--sp-ink);
}
.map-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.swatch {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  display: inline-block;
}
.swatch.high {
  background: #006d2c;
}
.swatch.medium {
  background: #31a354;
}
.swatch.low {
  background: #a1d99b;
}
.float-card {
  position: absolute;
  left: 22px;
  top: 58px;
  z-index: 2;
  width: min(400px, calc(100% - 44px));
  max-height: calc(100% - 300px);
  overflow-y: auto;
  background: var(--sp-cream);
  border-radius: 22px;
  padding: 24px 26px;
  box-shadow: 0 16px 40px #1d2a1d26;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.float-card h2 {
  font-size: 1.6rem;
  margin: 2px 0 4px;
}
.float-card.route-card h2 {
  font-size: 1.55rem;
}
.bubble-anchor {
  position: absolute;
  left: 22px;
  bottom: 22px;
  z-index: 2;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  max-width: calc(100% - 44px);
  pointer-events: none;
}
.bubble-anchor .sprout-bubble {
  margin-left: 0;
  max-width: 380px;
  pointer-events: auto;
}
.bubble-anchor .sprout-bubble::after {
  left: -8px;
  top: 24px;
  bottom: auto;
}
.route-facts {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.fact {
  flex: 1;
  min-width: 130px;
  border: 1px solid #e0dbcb;
  border-radius: 14px;
  padding: 10px 13px;
  background: white;
}
.fact span {
  display: block;
  font-size: 0.64rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #6b766a;
}
.fact strong {
  font-family: var(--sp-serif);
  font-size: 1.1rem;
}
.preference-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.preference-chip {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--sp-green);
  background: var(--sp-green-soft);
  border-radius: 999px;
  padding: 5px 11px;
}
.route-actions,
.step-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: 26px;
}
.step-nav-right {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 10px;
}
.step-nav-right .ghost-button,
.step-nav-right .primary-button {
  /* Overrides global.css's .primary-button { width: 100% } - without this,
     the button claims the whole row and only looked right by accident,
     because flex-shrink used to be free to crush it back down. */
  width: auto;
  flex-shrink: 0;
  white-space: nowrap;
}
.route-actions {
  justify-content: flex-start;
  margin-top: 4px;
}
.footnote {
  margin: 0;
  font-size: 0.74rem;
  color: #6b766a;
}
.route-note {
  margin: 0;
  font-size: 0.78rem;
  color: #8a6a2e;
  background: #f7ead2;
  border-radius: 10px;
  padding: 8px 12px;
}
.location-button {
  display: flex;
  gap: 7px;
  align-items: center;
  padding: 6px 0;
  border: none;
  background: none;
  color: var(--sp-green);
  font-weight: 700;
  font-size: 0.86rem;
  cursor: pointer;
}
.location-notice {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  color: #8a4a12;
}
.landmark-pills {
  margin: 4px 0;
}
.grow-button {
  width: 100%;
  min-height: 50px;
}
.primary-button {
  background: var(--sp-green);
  color: white;
  border: none;
  border-radius: 999px;
  padding: 13px 24px;
  font-family: var(--sp-sans);
  font-weight: 700;
  font-size: 0.92rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  box-shadow: 0 8px 18px #1f5a2c33;
}
.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}
.ghost-button {
  background: white;
  color: var(--sp-green);
  border: 1.5px solid var(--sp-green);
  border-radius: 999px;
  padding: 12px 22px;
  font-family: var(--sp-sans);
  font-weight: 700;
  font-size: 0.9rem;
  cursor: pointer;
}
.text-button {
  background: none;
  border: none;
  color: var(--sp-green);
  font-family: var(--sp-sans);
  font-weight: 700;
  font-size: 0.86rem;
  cursor: pointer;
  padding: 0;
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
@media (max-width: 900px) {
  .sprout-body {
    grid-template-columns: 1fr;
  }
  .sprout-stage {
    min-height: 0;
    padding-bottom: 24px;
  }
  .stage-figure {
    padding-bottom: 24px;
  }
  .sprout-panel {
    padding: 28px 22px;
  }
  .sprout-step h2 {
    font-size: 1.6rem;
  }
  .map-mode {
    height: auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .map-stage {
    position: relative;
    height: 380px;
  }
  .float-card,
  .bubble-anchor {
    position: relative;
    inset: auto;
    width: auto;
    max-width: none;
    margin: 12px 14px;
  }
  .float-card {
    max-height: none;
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
@media (prefers-reduced-motion: reduce) {
  .gauge-fill,
  .loading-ring {
    transition: none;
    animation: none;
  }
}
</style>
