<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Clock, Location as LocationIcon, QuestionFilled, Warning } from '@element-plus/icons-vue'
import GoogleMapCanvas from '@/components/GoogleMapCanvas.vue'
import SproutTree from '@/components/sprout/SproutTree.vue'
import GroundingSteps from '@/components/walk/GroundingSteps.vue'
import PinTreeFlow from '@/components/walk/PinTreeFlow.vue'
import StressCheckIn from '@/components/walk/StressCheckIn.vue'
import NearbyAreas from '@/components/rewards/NearbyAreas.vue'
import { MELBOURNE_CENTER, getZoneFacts, loadAllZones, type ZoneFacts } from '@/constants/zones'
import { getApprovedMessages, type PublicMessage } from '@/services/care.service'
import { decodePolyline } from '@/services/polyline'
import { canopyFriendProgress, visitNumber } from '@/services/rewards.logic'
import {
  ALMOST_RADIUS_M,
  ARRIVAL_RADIUS_M,
  FAR_FROM_ROUTE_M,
  OFF_ROUTE_M,
  TURN_ALERT_M,
  WEAK_GPS_ACCURACY_M,
  distanceM,
  findTurns,
  formatDistance,
  minutesLeft,
  nextOffRouteState,
  pickTip,
  progressAlong,
  zoneContaining,
  WALK_PACE_M_PER_MIN,
  type OffRouteState,
  type TipCandidate,
  type TipKind,
  type WalkProgress,
  DEMO_SPEED,
  pointAtDistance,
} from '@/services/walk'
import {
  ARRIVED_TEXT,
  BEYOND_BLUE,
  END_TEXT,
  HELP_TEXT,
  LOCATION_REASON,
  PAUSE_TEXT,
  REROUTE_QUESTION,
  RESUME_TEXT,
  WORSE_TEXT,
  almostTip,
  directionTip,
  treesTip,
  TIP_TEXT,
} from '@/data/walkMessages'
import { useJourneyStore } from '@/stores/journey'
import { useSproutStore } from '@/stores/sprout'
import { useRewardsStore } from '@/stores/rewards'
import type { Coordinates, TreeZone } from '@/types/discovery'
import type { AreaOption } from '@/types/planning'
import type { Mood } from '@/data/sproutMessages'

/**
 * Epic 6 live walk, then the arrival steps (Epic 7 pin and message) and the
 * stress check-in and rewards (Epic 8). Everything the walk knows about the
 * user's position stays on this device. The only thing sent to the server is
 * a tree pin or message the user chooses to post.
 */
type Phase = 'intro' | 'walking' | 'grounding' | 'pin' | 'checkin' | 'summary' | 'ended'

const router = useRouter()
const journey = useJourneyStore()
const sprout = useSproutStore()
const rewards = useRewardsStore()

const phase = ref<Phase>('intro')
/** searching: no fix yet. lost: signal dropped, still watching. denied: permission refused, for good. */
const gps = ref<'off' | 'searching' | 'on' | 'weak' | 'lost' | 'denied'>('off')
/** A simulated walk along the route, for demos far from the actual destination. */
const demoMode = ref(false)
/** The real position is too far from this route to track live. */
const farFromRoute = ref(false)
let demoTimer: ReturnType<typeof setInterval> | undefined
let demoMetres = 0
const position = ref<Coordinates | null>(null)
const accuracy = ref<number | null>(null)
const paused = ref(false)
const frozen = ref<WalkProgress | null>(null)
const worse = ref(false)
const helpOpen = ref(false)
const clock = ref(Date.now())
const zones = ref<TreeZone[]>([])
const tips = ref<{ id: number; kind: TipKind; text: string }[]>([])
const rerouteOpen = ref(false)
const rerouteDeclined = ref(false)
const pinMessages = ref<PublicMessage[]>([])
const openMessage = ref<PublicMessage | null>(null)
const sproutOverride = ref<string | null>(null)
const sproutFaceOverride = ref<'concerned' | 'grateful' | 'excited' | 'calm' | null>(null)
const summaryText = ref('')
const summaryDuplicate = ref(false)
const summaryAwarded = ref(0)
const summaryVisitNumber = ref(1)
const summaryFriend = ref<ReturnType<typeof canopyFriendProgress> | null>(null)

// Not reactive on purpose: these only drive timing decisions.
const shownKeys = new Set<string>()
let lastTipAt: number | null = null
let tipCounter = 0
let offRoute: OffRouteState = { offSince: null, shouldAsk: false }
let startedAt = 0
let pausedSince: number | null = null
let pausedTotalMs = 0
let watchId: number | null = null
let clockTimer: ReturnType<typeof setInterval> | undefined
let wakeLock: WakeLockSentinel | null = null

const WALK_STEPS = ['Walk', 'Arrive', 'Pin a tree', 'Message', 'Check in', 'Rewards']

/** Which of the six prototype steps the walk is on. */
/** What the pin-and-message flow is showing, reported by PinTreeFlow. */
const pinSay = ref('')
const pinStage = ref('pin')

const walkStepIndex = computed(() => {
  if (phase.value === 'grounding') return 1
  if (phase.value === 'pin') {
    return ['message', 'report', 'posted'].includes(pinStage.value) ? 3 : 2
  }
  if (phase.value === 'checkin') return 4
  if (phase.value === 'summary' || phase.value === 'ended') return 5
  return 0
})

const zoneId = computed(() => journey.destination?.id ?? null)
const destinationZone = computed<TreeZone | null>(() => zones.value.find((zone) => zone.id === zoneId.value) ?? null)
/** Real tree count and top species for the destination, from GET /api/zones/{id}/facts. */
const destinationFacts = ref<ZoneFacts | null>(null)

/**
 * The route actually being walked, normalised from whichever endpoint grew it.
 *
 * Sprout's own "grow a route" and "reroute from here" always call
 * POST /api/sprout/route, which picks the destination itself - that's
 * `journey.sproutRoute`. Choosing one specific area from "Find more trees
 * near you" needs an explicit destination, which only the older
 * POST /api/routes supports (`journey.route`); chooseArea() clears
 * `sproutRoute` when it does this, so this always prefers the current one.
 */
const activeRoute = computed(() => {
  const sproutRoute = journey.sproutRoute
  if (sproutRoute) {
    return {
      durationMinutes: sproutRoute.durationMinutes,
      distanceKm: sproutRoute.distanceMeters / 1000,
      denseZoneShare: sproutRoute.denseZoneShare as number | null,
      destinationTreeCount: sproutRoute.destination.treeCount as number | null,
      summaryChips: sproutRoute.summaryChips,
      path: decodePolyline(sproutRoute.encodedPolyline),
    }
  }
  const legacy = journey.route
  if (legacy) {
    return {
      durationMinutes: legacy.durationMinutes,
      distanceKm: legacy.distanceKm,
      denseZoneShare: legacy.metrics?.canopy != null ? legacy.metrics.canopy / 100 : null,
      destinationTreeCount: destinationZone.value?.treeCount ?? null,
      summaryChips: journey.summary,
      path: legacy.path && legacy.path.length > 1 ? legacy.path : [],
    }
  }
  return null
})

/** The walked route. Falls back to a straight line if neither endpoint sent a path. */
const path = computed<Coordinates[]>(() => {
  const points = activeRoute.value?.path
  if (points && points.length > 1) return points
  if (journey.startLocation && journey.destination) {
    return [journey.startLocation.coordinates, journey.destination.coordinates]
  }
  return []
})
const totalM = computed(() => (path.value.length > 1 ? progressAlong(path.value, path.value[0]!).totalM : 0))

const liveProgress = computed<WalkProgress | null>(() => {
  if (gps.value !== 'on' || !position.value || path.value.length < 2) return null
  return progressAlong(path.value, position.value)
})

/** Minutes walked by the clock, excluding paused time. Used when there is no GPS. */
const clockMinutes = computed(() => {
  if (!startedAt) return 0
  const pausedNow = pausedSince !== null ? clock.value - pausedSince : 0
  return Math.max(0, (clock.value - startedAt - pausedTotalMs - pausedNow) / 60_000)
})

const progress = computed(() => {
  if (paused.value && frozen.value) return frozen.value
  if (liveProgress.value) return liveProgress.value
  const walked = Math.min(totalM.value, clockMinutes.value * WALK_PACE_M_PER_MIN)
  return {
    walkedM: walked,
    totalM: totalM.value,
    remainingM: Math.max(0, totalM.value - walked),
    offRouteM: 0,
    segmentIndex: 0,
    snapped: path.value[0] ?? MELBOURNE_CENTER,
  } satisfies WalkProgress
})
const percent = computed(() => (totalM.value ? Math.round((progress.value.walkedM / totalM.value) * 100) : 0))

const walkedPath = computed<Coordinates[]>(() => {
  if (!liveProgress.value || paused.value) return []
  const index = progress.value.segmentIndex
  return [...path.value.slice(0, index + 1), progress.value.snapped]
})
const remainingPath = computed<Coordinates[]>(() => {
  if (!liveProgress.value) return path.value
  const index = progress.value.segmentIndex
  return [progress.value.snapped, ...path.value.slice(index + 1)]
})

const gpsLabel = computed(() => {
  if (demoMode.value) return 'LIVE WALK · DEMO'
  if (gps.value === 'on') return 'LIVE WALK · GPS ON'
  if (gps.value === 'weak') return 'LIVE WALK · GPS WEAK'
  if (gps.value === 'searching') return 'LIVE WALK · FINDING GPS'
  if (gps.value === 'lost') return 'LIVE WALK · GPS LOST'
  if (gps.value === 'denied') return 'LIVE WALK · NO GPS'
  return 'LIVE WALK'
})

const hasRoute = computed(() => path.value.length > 1)

const messagePins = computed(() =>
  pinMessages.value.map((message) => ({
    id: message.id,
    position: { lat: message.pin.latitude, lng: message.pin.longitude },
    label: message.body.slice(0, 60),
  })),
)

const sproutLine = computed(() => {
  if (sproutOverride.value) return sproutOverride.value
  if (phase.value === 'intro') return hasRoute.value ? 'Ready when you are. I’ll walk beside you.' : 'Grow a route first, then we can walk it.'
  if (phase.value === 'walking') {
    if (paused.value) return PAUSE_TEXT
    if (worse.value) return WORSE_TEXT
    return tips.value[0]?.text ?? 'Let’s walk. Take it at your own pace.'
  }
  if (phase.value === 'grounding') return ARRIVED_TEXT
  if (phase.value === 'pin') return pinSay.value
  if (phase.value === 'checkin') return 'How stressed do you feel now?'
  if (phase.value === 'ended') return END_TEXT
  return summaryText.value
})

const sproutFace = computed<'happy' | 'concerned' | 'excited' | 'calm' | 'grateful'>(() => {
  if (sproutFaceOverride.value) return sproutFaceOverride.value
  if (worse.value) return 'concerned'
  if (phase.value === 'grounding' || paused.value) return 'calm'
  if (phase.value === 'summary') return 'excited'
  return 'happy'
})

async function loadZones() {
  try {
    const result = await loadAllZones()
    zones.value = result.zones
  } catch {
    zones.value = []
  }
}

// ---- Tips -------------------------------------------------------------

/** Nearest tree zone to a point, for the street name in a DIRECTION tip. */
function nearestZone(point: Coordinates): TreeZone | null {
  let best: TreeZone | null = null
  let bestM = Infinity
  for (const zone of zones.value) {
    const d = distanceM(point, zone.center)
    if (d < bestM) {
      bestM = d
      best = zone
    }
  }
  return best
}

const turns = computed(() => findTurns(path.value))

function pushTip(kind: TipKind, key: string, text: string, now: number) {
  shownKeys.add(key)
  lastTipAt = now
  tips.value.unshift({ id: ++tipCounter, kind, text })
}

/** US6.3: pick at most one tip per cooldown, in priority order. */
function evaluateTips(now: number) {
  if (phase.value !== 'walking' || paused.value) return
  const candidates: TipCandidate[] = []
  const live = liveProgress.value
  const topSpecies = destinationFacts.value?.topSpecies.slice(0, 2).map((species) => species.commonName) ?? []
  const treeCount =
    destinationFacts.value?.treeCount ?? activeRoute.value?.destinationTreeCount ?? destinationZone.value?.treeCount ?? 0

  // Distance-based tips need GPS. Without it, the clock decides instead.
  const destination = journey.destination?.coordinates
  if (live && position.value) {
    if (destination && distanceM(position.value, destination) <= ALMOST_RADIUS_M) {
      candidates.push({ kind: 'almost', key: 'almost', text: almostTip(treeCount, topSpecies) })
    }
    for (const turn of turns.value) {
      if (turn.index <= live.segmentIndex) continue
      if (distanceM(position.value, turn.at) > TURN_ALERT_M) continue
      const street = nearestZone(turn.at)?.nearestStreet ?? null
      candidates.push({
        kind: 'direction',
        key: `turn-${turn.index}`,
        text: directionTip(street, turn.heading),
      })
    }
    const zone = zoneContaining(zones.value, position.value)
    if (zone && zone.density !== 'Low') {
      candidates.push({ kind: 'trees', key: `trees-${zone.id}`, text: treesTip(zone.density, zone.treeCount) })
    }
  } else {
    const remainingMinutes = minutesLeft(progress.value.remainingM)
    if (remainingMinutes <= 2) {
      candidates.push({ kind: 'almost', key: 'almost', text: almostTip(treeCount, topSpecies) })
    }
  }
  if (progress.value.walkedM >= totalM.value / 2 && totalM.value > 0) {
    candidates.push({ kind: 'checkin', key: 'checkin', text: TIP_TEXT.checkin })
  }
  // The breathe tip says the GPS is locked, so it only claims that when the
  // fix is actually good - weak/lost/denied all show their own "tips follow
  // the clock" note elsewhere on this screen, so the tip text must agree.
  if (gps.value !== 'searching') {
    const locked = gps.value === 'on'
    candidates.push({
      kind: 'breathe',
      key: 'breathe',
      text: locked ? TIP_TEXT.breathe : TIP_TEXT.breatheNoGps,
    })
  }

  const pick = pickTip(candidates, shownKeys, lastTipAt, now)
  if (pick) pushTip(pick.kind, pick.key, pick.text, now)
}

// ---- Position ----------------------------------------------------------

function onFix(fix: GeolocationPosition) {
  const now = Date.now()
  const hadNoFix = gps.value === 'searching' || gps.value === 'lost'
  accuracy.value = fix.coords.accuracy
  gps.value = fix.coords.accuracy > WEAK_GPS_ACCURACY_M ? 'weak' : 'on'
  position.value = { lat: fix.coords.latitude, lng: fix.coords.longitude }
  if (hadNoFix) sproutOverride.value = null
  if (paused.value || gps.value !== 'on') {
    evaluateTips(now)
    return
  }
  // Too far from the route for the real dot to follow it, so skip reroute prompts there.
  const live = liveProgress.value
  farFromRoute.value = !demoMode.value && (!live || live.offRouteM > FAR_FROM_ROUTE_M)
  if (live && !farFromRoute.value) {
    offRoute = nextOffRouteState(offRoute, live.offRouteM, now)
    if (offRoute.offSince === null) rerouteDeclined.value = false
    if (offRoute.shouldAsk && !rerouteDeclined.value) rerouteOpen.value = true
    const destination = journey.destination?.coordinates
    const atZone = destinationZone.value && zoneContaining([destinationZone.value], position.value)
    if ((destination && distanceM(position.value, destination) <= ARRIVAL_RADIUS_M) || atZone) {
      arrive()
      return
    }
  }
  evaluateTips(now)
}

/**
 * Permission refused (code 1) ends GPS for this walk. A timeout or a dropped
 * signal (codes 2 and 3) is temporary: keep the watch running, so the walk
 * picks the position back up when the phone finds it again.
 */
function onGeoError(error: GeolocationPositionError) {
  if (error.code === error.PERMISSION_DENIED) {
    gps.value = 'denied'
    stopTracking()
    sproutOverride.value = 'No GPS here, so I’ll keep time with you instead. Tips will come by the clock.'
  } else {
    gps.value = 'lost'
    sproutOverride.value = 'I lost the GPS signal for a moment. I’ll keep looking, and tips follow the clock meanwhile.'
  }
  evaluateTips(Date.now())
}

async function keepScreenOn() {
  try {
    wakeLock = (await navigator.wakeLock?.request('screen')) ?? null
  } catch {
    wakeLock = null
  }
}

function releaseScreen() {
  void wakeLock?.release().catch(() => undefined)
  wakeLock = null
}

function onVisibilityChange() {
  if (document.visibilityState === 'visible' && phase.value === 'walking') void keepScreenOn()
}

/** Simulated fixes along the route, through the same onFix path as a real position. */
function startDemo() {
  stopTracking()
  demoMode.value = true
  farFromRoute.value = false
  demoMetres = 0
  gps.value = 'on'
  void keepScreenOn()
  const tick = () => {
    const point = pointAtDistance(path.value, demoMetres)
    onFix({ coords: { latitude: point.lat, longitude: point.lng, accuracy: 5 } } as GeolocationPosition)
    demoMetres += WALK_PACE_M_PER_MIN * DEMO_SPEED / 60
    if (demoMetres > totalM.value) clearInterval(demoTimer)
  }
  demoTimer = setInterval(tick, 1_000)
  tick()
}

function switchToDemo() {
  if (!hasRoute.value) return
  startDemo()
}

function beginWalk(mode: 'gps' | 'none' | 'demo') {
  if (!hasRoute.value) return
  phase.value = 'walking'
  sproutOverride.value = null
  startedAt = Date.now()
  clock.value = startedAt
  void keepScreenOn()
  if (zoneId.value) {
    getZoneFacts(zoneId.value)
      .then((facts) => (destinationFacts.value = facts))
      .catch(() => (destinationFacts.value = null))
  }
  if (mode === 'demo') {
    startDemo()
    evaluateTips(startedAt)
    return
  }
  if (mode === 'gps' && navigator.geolocation) {
    // Not "on" until the first fix: the GPS-locked tip must wait for a real lock.
    gps.value = 'searching'
    watchId = navigator.geolocation.watchPosition(onFix, onGeoError, {
      enableHighAccuracy: true,
      maximumAge: 2_000,
      timeout: 20_000,
    })
  } else {
    gps.value = 'denied'
  }
  evaluateTips(startedAt)
}

function stopTracking() {
  if (watchId !== null) navigator.geolocation.clearWatch(watchId)
  watchId = null
  clearInterval(demoTimer)
  demoTimer = undefined
  releaseScreen()
}

// ---- Controls ----------------------------------------------------------

function togglePause() {
  const now = Date.now()
  if (paused.value) {
    paused.value = false
    frozen.value = null
    if (pausedSince !== null) pausedTotalMs += now - pausedSince
    pausedSince = null
    sproutOverride.value = RESUME_TEXT
    setTimeout(() => {
      if (sproutOverride.value === RESUME_TEXT) sproutOverride.value = null
    }, 4000)
  } else {
    frozen.value = progress.value
    paused.value = true
    pausedSince = now
    sproutOverride.value = null
  }
}

function feelingWorse() {
  worse.value = true
  sproutFaceOverride.value = 'concerned'
  paused.value = true
  frozen.value = progress.value
  if (pausedSince === null) pausedSince = Date.now()
}

function endWalk() {
  stopTracking()
  rerouteOpen.value = false
  phase.value = 'ended'
  paused.value = false
  pausedSince = null
}

function answerReroute(yes: boolean) {
  rerouteOpen.value = false
  if (!yes) {
    rerouteDeclined.value = true
    return
  }
  if (!position.value) return
  journey.startLocation = {
    id: 'walk-from-here',
    label: 'Your location',
    coordinates: { ...position.value },
  }
  offRoute = { offSince: null, shouldAsk: false }
  void journey.growSproutRoute()
}

async function arrive() {
  if (phase.value !== 'walking') return
  stopTracking()
  phase.value = 'grounding'
  sproutFaceOverride.value = 'calm'
  try {
    if (zoneId.value) pinMessages.value = await getApprovedMessages(zoneId.value)
  } catch {
    pinMessages.value = []
  }
}

function onMessagePin(id: string) {
  openMessage.value = pinMessages.value.find((message) => message.id === id) ?? null
}

function toPin() {
  phase.value = 'pin'
  sproutFaceOverride.value = null
}

function toCheckIn() {
  phase.value = 'checkin'
  sproutFaceOverride.value = null
}

function logVisit(after: Mood | null) {
  if (!zoneId.value) return
  const before = sprout.mood
  const number = visitNumber(rewards.state, zoneId.value)
  const result = rewards.logVisit({
    zoneId: zoneId.value,
    label: journey.destination?.label,
    before,
    after,
  })
  summaryAwarded.value = result.awarded
  summaryDuplicate.value = result.duplicate
  summaryVisitNumber.value = number
  summaryFriend.value = canopyFriendProgress(rewards.state, zoneId.value, new Date())
  summaryText.value = result.duplicate
    ? 'You already logged this area today, so no extra points this time. Thanks for coming back, though.'
    : `You earned ${result.awarded} leaf points! Visit new tree-dense areas to unlock new looks for me.`
  phase.value = 'summary'
  sproutFaceOverride.value = 'excited'
}

async function chooseArea(area: AreaOption) {
  journey.destination = {
    id: area.destination.zoneId,
    label: area.destination.label,
    coordinates: area.destination.center,
  }
  // The user picked this exact area, so the backend-chosen route from Sprout's
  // own grow/reroute calls no longer applies - /api/routes takes a destination.
  journey.sproutRoute = null
  await journey.calculate('WALK')
  destinationFacts.value = null
  phase.value = 'intro'
  summaryText.value = ''
  tips.value = []
  shownKeys.clear()
  lastTipAt = null
  paused.value = false
  worse.value = false
  pausedTotalMs = 0
  pausedSince = null
  startedAt = 0
  sproutFaceOverride.value = null
}

function visitAnother() {
  router.push('/')
}

// ---- Lifecycle ---------------------------------------------------------

onMounted(() => {
  void loadZones()
  clockTimer = setInterval(() => {
    clock.value = Date.now()
    // Without GPS, tips follow the clock, one at a time, respecting the cooldown.
    if (phase.value === 'walking' && !paused.value && gps.value !== 'on') {
      evaluateTips(clock.value)
    }
  }, 1_000)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onBeforeUnmount(() => {
  stopTracking()
  clearInterval(clockTimer)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

const arrivalCenter = computed(() => journey.destination?.coordinates ?? MELBOURNE_CENTER)
const mapCenterAuto = computed(() => phase.value === 'grounding')
</script>

<template>
  <div class="walk-page">
    <header class="walk-header">
      <nav class="walk-steps" aria-label="Walk steps">
        <span
          v-for="(item, index) in WALK_STEPS"
          :key="item"
          class="walk-step"
          :class="{ done: index < walkStepIndex, active: index === walkStepIndex }"
        >
          <span class="walk-dot">
            <template v-if="index < walkStepIndex">✓</template>
            <template v-else>{{ index + 1 }}</template>
          </span>
          {{ item }}
        </span>
      </nav>
      <span class="live-label" :class="gps">{{ gpsLabel }}</span>
      <div class="help-wrap">
        <button
          type="button"
          class="help-button"
          :aria-expanded="helpOpen"
          @click="helpOpen = !helpOpen"
        >
          <ElIcon><QuestionFilled /></ElIcon> Help
        </button>
        <div v-if="helpOpen" class="help-panel" role="note">
          <p>{{ HELP_TEXT }}</p>
          <p>If things feel heavy, talk to someone. {{ BEYOND_BLUE.label }}: <strong>{{ BEYOND_BLUE.number }}</strong></p>
        </div>
      </div>
      <RouterLink class="text-button" to="/">Back to Sprout</RouterLink>
    </header>

    <div v-if="!hasRoute" class="empty-state">
      <p>Grow a route with Sprout first, then you can start the walk here.</p>
      <RouterLink class="primary-button" to="/">Go to Sprout</RouterLink>
    </div>

    <div v-else class="walk-layout">
      <section class="map-column" aria-label="Walk map">
        <div class="walk-map">
          <GoogleMapCanvas
            :center="mapCenterAuto ? arrivalCenter : MELBOURNE_CENTER"
            :trees="[]"
            :zones="zones"
            :directions-open="false"
            :route-options="[]"
            :origin="journey.startLocation?.coordinates"
            :destination="journey.destination?.coordinates"
            :walked-path="walkedPath"
            :remaining-path="remainingPath"
            :user-position="gps === 'on' ? position : null"
            :message-pins="messagePins"
            :auto-center="mapCenterAuto"
            @select-message="onMessagePin"
          />
          <div class="live-card">
            <span class="eyebrow">LIVE GPS</span>
            <strong>{{ journey.startLocation?.label }} → {{ journey.destination?.label }}</strong>
          </div>
          <div class="walk-legend" aria-label="Map legend">
            <span><i class="swatch high" />High</span>
            <span><i class="swatch medium" />Medium</span>
            <span><i class="swatch low" />Low</span>
            <span><i class="you-dot" />You</span>
          </div>
        </div>
      </section>

      <section class="panel">
        <!-- Sprout, always in view at the top of the panel, as in the prototype -->
        <div class="panel-head">
          <SproutTree :size="96" :face="sproutFace" :canopy="null" />
          <div class="bubble" role="status">
            <span class="eyebrow">SPROUT SAYS</span>
            <p>{{ sproutLine }}</p>
          </div>
        </div>

        <!-- Intro: explain location, then start -->
        <template v-if="phase === 'intro'">
          <article class="route-card">
            <span class="eyebrow">PERSONALISED WALKING ROUTE</span>
            <h2>Walking to {{ journey.destination?.label }}</h2>
            <p class="from">From {{ journey.startLocation?.label }}</p>
            <div class="facts">
              <div class="fact"><span>Walk time</span><strong>{{ activeRoute?.durationMinutes }} min</strong></div>
              <div class="fact"><span>Distance</span><strong>{{ activeRoute?.distanceKm.toFixed(1) }} km</strong></div>
              <div v-if="activeRoute?.destinationTreeCount != null" class="fact">
                <span>Area trees</span><strong>{{ activeRoute.destinationTreeCount }}</strong>
              </div>
              <div v-if="activeRoute?.denseZoneShare != null" class="fact">
                <span>Tree-dense share</span><strong>{{ Math.round(activeRoute.denseZoneShare * 100) }}%</strong>
              </div>
            </div>
            <div v-if="activeRoute?.summaryChips.length" class="chips">
              <span v-for="chip in activeRoute.summaryChips" :key="chip" class="chip">{{ chip }}</span>
            </div>
          </article>
          <p class="reason">{{ LOCATION_REASON }}</p>
          <div class="row">
            <button type="button" class="primary-button" @click="beginWalk('gps')">
              <ElIcon><LocationIcon /></ElIcon> Start walk
            </button>
            <button type="button" class="ghost-button" @click="beginWalk('demo')">Demo walk</button>
            <button type="button" class="ghost-button" @click="beginWalk('none')">Walk without GPS</button>
          </div>
        </template>

        <!-- Live walk -->
        <template v-else-if="phase === 'walking'">
          <div class="walking-to">
            <span class="eyebrow">WALKING TO</span>
            <h2>{{ journey.destination?.label }}</h2>
            <p class="from">
              From {{ journey.startLocation?.label }} · {{ activeRoute?.durationMinutes }} min ·
              {{ activeRoute?.distanceKm.toFixed(1) }} km
              <template v-if="activeRoute?.destinationTreeCount != null"> · {{ activeRoute.destinationTreeCount }} trees</template>
            </p>
          </div>
          <div v-if="activeRoute?.summaryChips.length" class="chips">
            <span v-for="chip in activeRoute.summaryChips" :key="chip" class="chip">{{ chip }}</span>
          </div>
          <div class="progress-block">
            <div class="progress-head">
              <strong>{{ percent }}% of the route</strong>
              <span class="muted">{{ formatDistance(progress.remainingM) }} left · {{ minutesLeft(progress.remainingM) }} min</span>
            </div>
            <div class="bar" role="progressbar" :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100">
              <div class="bar-fill" :style="{ width: `${percent}%` }" />
            </div>
            <p v-if="gps === 'weak'" class="weak-note" role="status">
              <ElIcon><Warning /></ElIcon> GPS signal weak. Tips follow the clock for now.
            </p>
            <div v-if="farFromRoute && !demoMode" class="reroute" role="status">
              <p>
                Your live location is too far from this route to track. Try the demo walk to see the full flow.
              </p>
              <button type="button" class="primary-button" @click="switchToDemo">Switch to demo walk</button>
            </div>
            <p v-if="demoMode" class="muted small">Demo walk: a simulated position moves along the route at {{ DEMO_SPEED }}× speed.</p>
            <p v-if="gps === 'lost'" class="weak-note" role="status">
              <ElIcon><Warning /></ElIcon> GPS signal lost. I’m still looking; tips follow the clock.
            </p>
            <p v-if="gps === 'denied'" class="muted small">
              No GPS mode. Your route is shown and tips come by time.
            </p>
          </div>

          <aside v-if="rerouteOpen" class="reroute" role="alert">
            <p>{{ REROUTE_QUESTION }}</p>
            <div class="row">
              <button type="button" class="primary-button" @click="answerReroute(true)">Yes</button>
              <button type="button" class="ghost-button" @click="answerReroute(false)">No</button>
            </div>
          </aside>

          <div class="controls">
            <button type="button" class="primary-button wide" @click="arrive">I’ve arrived</button>
            <div class="row">
              <button type="button" class="ghost-button" @click="togglePause">
                {{ paused ? 'Keep walking' : 'I need a break' }}
              </button>
              <button type="button" class="ghost-button" @click="feelingWorse">I’m feeling worse</button>
            </div>
            <button type="button" class="text-button danger" @click="endWalk">End walk</button>
          </div>

          <div v-if="tips.length" class="tips">
            <span class="eyebrow">SPROUT’S LIVE TIPS</span>
            <ul>
              <li v-for="tip in tips" :key="tip.id">
                <span class="tag">{{ tip.kind.toUpperCase() === 'CHECKIN' ? 'CHECK IN' : tip.kind.toUpperCase() }}</span>
                {{ tip.text }}
              </li>
            </ul>
          </div>
        </template>

        <!-- Arrival: grounding -->
        <template v-else-if="phase === 'grounding'">
          <p class="reached">You’ve reached your tree-dense area</p>
          <p v-if="rewards.state.visits.some((v) => v.zoneId === zoneId)" class="came-back">
            You came back! This is visit {{ visitNumber(rewards.state, zoneId ?? '') }} to this area.
          </p>
          <article class="here">
            <span class="eyebrow">YOU’RE HERE</span>
            <strong
              >{{ journey.destination?.label }} ·
              {{ destinationFacts?.treeCount ?? destinationZone?.treeCount ?? 0 }} trees</strong
            >
          </article>
          <GroundingSteps @done="toPin" />
          <div v-if="pinMessages.length" class="messages">
            <span class="eyebrow">MESSAGES FROM OTHER VISITORS</span>
            <ul>
              <li v-for="message in pinMessages" :key="message.id">
                <button type="button" class="text-button" @click="onMessagePin(message.id)">{{ message.body.slice(0, 50) }}</button>
              </li>
            </ul>
            <p v-if="openMessage" class="open-message">{{ openMessage.body }}</p>
          </div>
        </template>

        <!-- Epic 7: pin, photo, message -->
        <template v-else-if="phase === 'pin'">
          <PinTreeFlow
            :zone-id="zoneId"
            :landmark="destinationZone?.nearestStreet ?? journey.destination?.label ?? 'this area'"
            @face="(f) => (sproutFaceOverride = f)"
            @say="(text) => (pinSay = text)"
            @stage="(next) => (pinStage = next)"
            @done="toCheckIn"
          />
        </template>

        <!-- Epic 6 check-in, Epic 8 rewards -->
        <template v-else-if="phase === 'checkin'">
          <StressCheckIn :before="sprout.mood" @log="logVisit" />
        </template>

        <template v-else-if="phase === 'summary'">
          <article class="summary">
            <span class="eyebrow">{{ summaryDuplicate ? 'ALREADY LOGGED TODAY' : 'WALK COMPLETE' }}</span>
            <h2 v-if="!summaryDuplicate">+{{ summaryAwarded }} leaf points</h2>
            <p class="muted">New total: {{ rewards.state.points }} leaf points</p>
            <p v-if="summaryVisitNumber === 1 && !summaryDuplicate" class="badge">
              You helped care for this area. Visit {{ summaryFriend?.visitsNeeded }} more times this week to become a Canopy Friend.
            </p>
            <p v-if="summaryFriend?.earned" class="badge friend">Canopy Friend</p>
            <p class="muted small">Points and visits are saved on this device only. No account needed.</p>
          </article>
          <NearbyAreas @pick="chooseArea" />
          <button type="button" class="primary-button" @click="visitAnother">Done</button>
        </template>

        <!-- Ended early: no failure message, just thanks -->
        <template v-else-if="phase === 'ended'">
          <article class="summary">
            <p>{{ END_TEXT }}</p>
          </article>
          <button type="button" class="primary-button" @click="visitAnother">Back to Sprout</button>
        </template>
      </section>
    </div>

  </div>
</template>

<style scoped>
.walk-page {
  --sp-serif: 'Fraunces', Georgia, serif;
  /* #app has no fixed height, so percentages would collapse: fill the viewport. */
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: 'Figtree', system-ui, sans-serif;
  background: #f5f2e8;
  color: #1d2a1d;
}
.walk-steps {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
  flex: 1;
}
.walk-step {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 0.8rem;
  font-weight: 600;
  color: #7a8478;
  padding: 5px 10px 5px 5px;
  border-radius: 999px;
}
.walk-step.done {
  color: #1d2a1d;
}
.walk-step.active {
  background: #1f5a2c;
  color: white;
}
.walk-dot {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ece8da;
  font-size: 0.7rem;
  font-weight: 700;
}
.walk-step.done .walk-dot {
  background: #1f5a2c;
  color: white;
}
.walk-step.active .walk-dot {
  background: white;
  color: #1f5a2c;
}
.live-card {
  position: absolute;
  left: 16px;
  top: 14px;
  z-index: 2;
  background: white;
  border-radius: 14px;
  padding: 10px 14px;
  box-shadow: 0 6px 18px #1d2a1d1f;
  max-width: 70%;
  font-size: 0.86rem;
}
.live-card strong {
  display: block;
  margin-top: 2px;
}
.walk-legend {
  position: absolute;
  left: 16px;
  bottom: 16px;
  z-index: 2;
  display: flex;
  gap: 12px;
  align-items: center;
  background: white;
  border-radius: 12px;
  padding: 8px 12px;
  box-shadow: 0 6px 18px #1d2a1d1f;
  font-size: 0.74rem;
}
.walk-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.walk-legend .swatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  display: inline-block;
}
.walk-legend .swatch.high {
  background: #006d2c;
}
.walk-legend .swatch.medium {
  background: #31a354;
}
.walk-legend .swatch.low {
  background: #a1d99b;
}
.you-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #1a73e8;
  display: inline-block;
}
.panel-head {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #eef3e6;
  border-radius: 18px;
  padding: 12px 16px;
  margin: -20px -28px 4px;
}
.here {
  background: white;
  border: 1px solid #e0dbcb;
  border-radius: 14px;
  padding: 10px 14px;
  display: grid;
  gap: 2px;
}
.walking-to h2 {
  font-family: var(--sp-serif, Georgia, serif);
  font-size: 1.5rem;
  margin: 2px 0 4px;
}
.walking-to .from {
  margin: 0;
  font-size: 0.86rem;
  color: #6b766a;
}
.controls .wide {
  width: 100%;
}
.walk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 12px 24px;
  background: white;
  border-bottom: 1px solid var(--tg-border);
}
.live-label {
  margin-right: 16px;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: var(--tg-green-800);
}
.live-label.denied,
.live-label.weak {
  color: #8a4a12;
}
.walk-layout {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
  min-height: 0;
}
.panel {
  min-height: 0;
}
.map-column {
  display: flex;
  flex-direction: column;
  padding: 20px 24px;
  gap: 14px;
  min-height: 0;
}
.walk-map {
  position: relative;
  flex: 1;
  min-height: 420px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--tg-border);
}
.sprout-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}
.bubble {
  background: white;
  border: 1.5px solid var(--tg-green-100);
  border-radius: 18px;
  padding: 12px 16px;
  max-width: 420px;
}
.bubble p {
  margin: 4px 0 0;
  font-size: 0.92rem;
  line-height: 1.45;
  color: var(--tg-green-950);
}
.panel {
  padding: 20px 28px;
  overflow-y: auto;
  display: grid;
  gap: 16px;
  align-content: start;
}
.eyebrow {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: var(--tg-green-700);
}
h2 {
  margin: 4px 0;
  font-size: 1.15rem;
}
.route-card {
  background: white;
  border: 1px solid var(--tg-border);
  border-radius: 16px;
  padding: 16px;
}
.from,
.muted {
  margin: 0;
  color: var(--tg-muted);
  font-size: 0.86rem;
}
.small {
  font-size: 0.78rem;
}
.facts {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.fact {
  flex: 1;
  min-width: 110px;
  border: 1px solid var(--tg-border);
  border-radius: 12px;
  padding: 10px 12px;
}
.fact span {
  display: block;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--tg-muted);
}
.chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.chip,
.tag {
  font-size: 0.72rem;
  font-weight: 700;
  border-radius: 999px;
  padding: 4px 10px;
  background: var(--tg-green-100);
  color: var(--tg-green-900);
}
.tag {
  border-radius: 6px;
  letter-spacing: 0.06em;
  margin-right: 6px;
}
.reason {
  font-size: 0.82rem;
  color: var(--tg-muted);
  margin: 0;
}
.row,
.controls {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.progress-block {
  display: grid;
  gap: 8px;
}
.progress-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.bar {
  height: 10px;
  border-radius: 999px;
  background: var(--tg-green-50);
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: var(--tg-green-700);
  transition: width 400ms ease;
}
.weak-note {
  margin: 0;
  color: #8a4a12;
  font-size: 0.84rem;
  display: flex;
  gap: 6px;
  align-items: center;
}
.reroute {
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 0.9rem;
  border: 1.5px solid #e9b98a;
  background: #fff6ec;
}
.reroute p {
  margin: 0 0 8px;
}
.help-wrap {
  position: relative;
}
.help-button {
  display: flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: none;
  padding: 0;
  font-size: 0.84rem;
  font-weight: 700;
  color: var(--tg-green-700);
  cursor: pointer;
}
.help-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  z-index: 5;
  width: 260px;
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 0.86rem;
  background: #eef4fb;
  box-shadow: 0 10px 24px #1d2a1d26;
}
.help-panel p {
  margin: 0 0 8px;
}
.help-panel p:last-child {
  margin-bottom: 0;
}
.tips ul,
.messages ul {
  list-style: none;
  margin: 6px 0 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.tips li {
  font-size: 0.88rem;
  line-height: 1.45;
}
.reached {
  margin: 0;
  font-weight: 800;
  font-size: 1rem;
  color: var(--tg-green-900);
}
.came-back,
.badge {
  margin: 0;
  font-size: 0.9rem;
  color: var(--tg-green-900);
}
.badge.friend {
  display: inline-block;
  font-weight: 800;
  background: var(--tg-green-100);
  border-radius: 999px;
  padding: 4px 12px;
  width: fit-content;
  animation: pop 500ms ease-out;
}
@keyframes pop {
  0% {
    transform: scale(0.6);
    opacity: 0;
  }
  70% {
    transform: scale(1.08);
    opacity: 1;
  }
  100% {
    transform: scale(1);
  }
}
.open-message {
  background: #fff7e6;
  border-radius: 12px;
  padding: 10px 12px;
  margin: 8px 0 0;
  font-size: 0.9rem;
}
.summary {
  background: white;
  border: 1px solid var(--tg-border);
  border-radius: 16px;
  padding: 16px;
  display: grid;
  gap: 6px;
}
.empty-state {
  margin: 48px auto;
  text-align: center;
  display: grid;
  gap: 12px;
  justify-items: center;
}
.primary-button,
.ghost-button {
  border-radius: 999px;
  padding: 12px 20px;
  font-weight: 700;
  font-size: 0.88rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  text-decoration: none;
}
.primary-button {
  background: var(--tg-green-800);
  color: white;
  border: none;
}
.ghost-button {
  background: white;
  color: var(--tg-green-800);
  border: 1.5px solid var(--tg-green-800);
}
.text-button {
  background: none;
  border: none;
  color: var(--tg-green-700);
  font-weight: 700;
  font-size: 0.84rem;
  cursor: pointer;
  text-decoration: none;
}
.text-button.danger {
  color: #b44235;
}
@media (max-width: 800px) {
  .walk-layout {
    grid-template-columns: 1fr;
  }
  .walk-map {
    flex: none;
    height: 280px;
    min-height: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .bar-fill,
  .badge.friend {
    transition: none;
    animation: none;
  }
}
</style>
