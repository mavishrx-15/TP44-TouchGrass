<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Location as LocationIcon, Warning } from '@element-plus/icons-vue'
import CameraCapture from '@/components/walk/CameraCapture.vue'
import {
  PHOTO_DONE,
  PIN_QUESTION,
  PIN_WARNING,
  MESSAGE_PROMPT,
  PINNED_TEXT,
  POSTED_TEXT,
  REPORT_SENT_TEXT,
  SAVED_NOTE,
  THANKS_CHIP,
  DAMAGE_CHIP,
  damageNotice,
  findDamageWord,
  friendlyError,
} from '@/data/walkMessages'
import {
  createPin,
  postMessage,
  updatePinPhoto,
  type CareMessage,
  type CarePin,
} from '@/services/care.service'
import { WEAK_GPS_ACCURACY_M } from '@/services/walk'

/**
 * Epic 7 in one flow: pin the tree you are next to (US7.1), photograph it
 * (US7.2), write to it (US7.3), and turn damage words into a report (US7.4).
 * Nothing leaves the phone until the user taps a send or post button.
 */
const props = defineProps<{
  zoneId: string | null
  /** The nearest street or landmark, used on the damage report. */
  landmark: string
}>()

const emit = defineEmits<{
  done: []
  face: [face: 'concerned' | 'grateful' | 'excited']
  // The walk screen shows these in Sprout's bubble and in the step bar.
  say: [text: string]
  stage: [stage: Stage]
}>()

const MAX_BODY = 500

type Stage = 'pin' | 'pinned' | 'photo' | 'message' | 'report' | 'posted'

const stage = ref<Stage>('pin')
const pin = ref<CarePin | null>(null)
const pinning = ref(false)
const pinError = ref('')
const weakSignal = ref(false)
const liveAccuracy = ref<number | null>(null)
const coordinates = ref<{ lat: number; lng: number } | null>(null)
const photoUrl = ref<string | null>(null)
const photoError = ref('')
const body = ref('')
const sending = ref(false)
const sendError = ref('')
const lastPosted = ref<string>('')
const posted = ref<{ id: string; kind: CareMessage['kind']; body: string; at: string }[]>([])

const damageWord = computed(() => findDamageWord(body.value))

/** Sprout's line for the current stage, shown by the walk screen. */
const sproutSays = computed(() => {
  if (stage.value === 'pin') return PIN_QUESTION
  if (stage.value === 'pinned') return PINNED_TEXT
  if (stage.value === 'photo') return 'Take a photo of your tree, or skip it.'
  if (stage.value === 'report') return damageNotice(damageWord.value ?? 'damage')
  if (stage.value === 'posted') return lastPosted.value
  if (damageWord.value) return damageNotice(damageWord.value)
  return MESSAGE_PROMPT
})

watch(sproutSays, (text) => emit('say', text), { immediate: true })
watch(stage, (next) => emit('stage', next), { immediate: true })

function readPosition(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Location is not available on this device.'))
      return
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 15_000,
      maximumAge: 0,
    })
  })
}

async function dropPin(allowWeak = false) {
  pinning.value = true
  pinError.value = ''
  try {
    const fix = await readPosition()
    const accuracy = fix.coords.accuracy
    liveAccuracy.value = Math.round(accuracy)
    if (!allowWeak && accuracy > WEAK_GPS_ACCURACY_M) {
      weakSignal.value = true
      return
    }
    weakSignal.value = false
    const saved = await createPin({
      zoneId: props.zoneId,
      latitude: fix.coords.latitude,
      longitude: fix.coords.longitude,
      accuracyM: accuracy,
      photoDataUrl: null,
    })
    pin.value = saved
    coordinates.value = { lat: saved.latitude, lng: saved.longitude }
    stage.value = 'pinned'
    emit('face', 'excited')
  } catch (e) {
    pinError.value = friendlyError(e, 'The pin could not be placed.')
  } finally {
    pinning.value = false
  }
}

async function onPhoto(dataUrl: string) {
  if (!pin.value) return
  photoError.value = ''
  try {
    const updated = await updatePinPhoto(pin.value.id, dataUrl)
    pin.value = updated
    photoUrl.value = dataUrl
    stage.value = 'message'
    lastPosted.value = PHOTO_DONE
  } catch (e) {
    photoError.value = friendlyError(e, 'The photo could not be saved.')
  }
}

/** A quick phrase goes on its own line as a full sentence, as the prototype adds it to the message. */
function addChip(text: string) {
  const sentence = text.endsWith('.') ? text : `${text}.`
  const current = body.value.trimEnd()
  const next = current ? `${current}\n${sentence}` : sentence
  body.value = next.slice(0, MAX_BODY)
}

function reviewOrPost() {
  if (!body.value.trim()) return
  if (damageWord.value) {
    stage.value = 'report'
    emit('face', 'concerned')
    return
  }
  void sendMessage('message')
}

async function sendMessage(kind: CareMessage['kind']) {
  if (!pin.value) return
  sending.value = true
  sendError.value = ''
  // Open the share sheet first, while the tap still counts as a user gesture.
  // Some phones refuse navigator.share after the network call below.
  const sharing = kind === 'damage_report' ? shareReport() : null
  try {
    const message = await postMessage(pin.value.id, body.value.trim(), kind)
    posted.value = [
      { id: message.id, kind, body: message.body, at: new Date().toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit' }) },
      ...posted.value,
    ]
    if (sharing) {
      await sharing
      lastPosted.value = REPORT_SENT_TEXT
      emit('face', 'grateful')
    } else {
      lastPosted.value = POSTED_TEXT
      emit('face', 'grateful')
    }
    body.value = ''
    stage.value = 'posted'
  } catch (e) {
    sendError.value = friendlyError(e, 'The message could not be sent.')
  } finally {
    sending.value = false
  }
}

/** US7.4: hand the report to the phone's share sheet or email app. Only after a tap. */
async function shareReport() {
  const today = new Date().toLocaleDateString('en-AU')
  const where = coordinates.value
    ? `${coordinates.value.lat.toFixed(5)}, ${coordinates.value.lng.toFixed(5)} (near ${props.landmark})`
    : props.landmark
  const text = [
    'Possible tree damage reported through TouchGrass.',
    `Location: ${where}`,
    `Photo attached: ${photoUrl.value ? 'yes' : 'no'}`,
    `What was seen: ${body.value.trim()}`,
    `Date: ${today}`,
  ].join('\n')
  const subject = 'Possible tree damage report'
  try {
    if (navigator.share) {
      await navigator.share({ title: subject, text })
    } else {
      window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(text)}`
    }
  } catch {
    // The user cancelled the share sheet. The report is already saved in TouchGrass.
  }
}

function startAnother() {
  body.value = ''
  stage.value = 'message'
}

function finish() {
  emit('done')
}
</script>

<template>
  <div class="pin-flow">
    <!-- US7.1 Pin the tree -->
    <section v-if="stage === 'pin'" class="pin-step">
      <h2>Pin the tree you’re with</h2>
      <p class="pin-note">Stand next to your tree. I’ll drop a pin at your live location, then you can snap a photo.</p>
      <button type="button" class="primary-button" :disabled="pinning" @click="dropPin()">
        <ElIcon><LocationIcon /></ElIcon>{{ pinning ? 'Finding your position…' : 'Drop a pin here' }}
      </button>
      <div v-if="weakSignal" class="weak" role="alert">
        <p><ElIcon><Warning /></ElIcon> {{ PIN_WARNING }} (accuracy about {{ liveAccuracy }} m)</p>
        <div class="row">
          <button type="button" class="ghost-button" @click="dropPin()">Wait and try again</button>
          <button type="button" class="text-button" @click="dropPin(true)">Pin it anyway</button>
        </div>
      </div>
      <p v-if="pinError" class="form-error" role="alert">{{ pinError }}</p>
    </section>

    <!-- The pin card, shown once a pin exists -->
    <div v-if="pin" class="pin-card">
      <span class="eyebrow">YOUR TREE PIN</span>
      <p class="coords">{{ pin.latitude.toFixed(5) }}, {{ pin.longitude.toFixed(5) }}</p>
      <p class="accuracy">
        Pinned at your live location, right next to your tree (accuracy about {{ Math.round(pin.accuracyM) }} m).
      </p>
    </div>

    <!-- Pinned: the prototype's three choices -->
    <section v-if="stage === 'pinned'" class="row pinned-actions">
      <button type="button" class="primary-button" @click="stage = 'photo'">Take a photo of your tree</button>
      <button type="button" class="ghost-button" @click="stage = 'message'">Write a message</button>
      <button type="button" class="text-button" @click="stage = 'message'">Not now</button>
    </section>

    <!-- US7.2 Photo -->
    <section v-if="stage === 'photo'" class="photo-step">
      <CameraCapture @captured="onPhoto" @cancel="stage = photoUrl ? 'message' : 'pinned'" />
      <p v-if="photoError" class="form-error" role="alert">{{ photoError }}</p>
    </section>

    <!-- US7.3 / US7.4 Message and report -->
    <section v-if="stage === 'message' || stage === 'report'" class="message-step">
      <div v-if="stage === 'message'">
        <div class="pin-summary">
          <img v-if="photoUrl" :src="photoUrl" alt="" class="pin-thumb-img" />
          <span v-else class="pin-thumb" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24"><path d="M4 8h3l2-3h6l2 3h3v11H4z" fill="none" stroke="#1f5a2c" stroke-width="1.8" stroke-linejoin="round" /><circle cx="12" cy="13" r="3.5" fill="none" stroke="#1f5a2c" stroke-width="1.8" /></svg>
          </span>
          <div>
            <strong>Your pinned tree near {{ landmark }}</strong>
            <small>
              Pinned at {{ pin?.latitude.toFixed(5) }}, {{ pin?.longitude.toFixed(5) }} · {{ photoUrl ? 'photo attached' : 'no photo' }}
            </small>
          </div>
        </div>
        <label class="field-label" for="tree-message">Your message to this tree</label>
        <textarea
          id="tree-message"
          v-model="body"
          :maxlength="MAX_BODY"
          rows="4"
          placeholder="Say thanks, or tell us what you see"
        />
        <div class="row chips-row">
          <button v-if="!photoUrl" type="button" class="ghost-button" @click="stage = 'photo'">Take a photo of your tree</button>
          <button type="button" class="chip" @click="addChip(THANKS_CHIP)">+ {{ THANKS_CHIP }}</button>
          <button type="button" class="chip" @click="addChip(DAMAGE_CHIP)">+ {{ DAMAGE_CHIP }}</button>
        </div>
        <div class="row">
          <button type="button" class="primary-button" :disabled="!body.trim() || sending" @click="reviewOrPost">
            {{ damageWord ? 'Review damage report' : 'Post message to this tree' }}
          </button>
        </div>
        <p class="saved-note">{{ SAVED_NOTE }}</p>
      </div>

      <!-- Damage report preview: nothing is sent until a button is tapped -->
      <div v-else class="report">
        <h3>Damage report preview</h3>
        <dl>
          <dt>Tree</dt>
          <dd>Pinned tree, {{ pin?.latitude.toFixed(5) }}, {{ pin?.longitude.toFixed(5) }}</dd>
          <dt>Nearest landmark</dt>
          <dd>{{ landmark }}</dd>
          <dt>Photo attached</dt>
          <dd>{{ photoUrl ? 'Yes' : 'No' }}</dd>
          <dt>What was seen</dt>
          <dd>“{{ body }}”</dd>
          <dt>Date</dt>
          <dd>{{ new Date().toLocaleDateString('en-AU') }}</dd>
        </dl>
        <div class="row">
          <button type="button" class="primary-button" :disabled="sending" @click="sendMessage('damage_report')">
            Send damage report with photo
          </button>
          <button type="button" class="ghost-button" :disabled="sending" @click="sendMessage('message')">
            Just post it as a message
          </button>
          <button type="button" class="text-button" @click="stage = 'message'">Edit</button>
        </div>
      </div>
      <p v-if="sendError" class="form-error" role="alert">{{ sendError }}</p>
    </section>

    <!-- Posted -->
    <section v-if="stage === 'posted'" class="posted-step">
      <div class="row">
        <button type="button" class="ghost-button" @click="startAnother">Write another message</button>
        <button type="button" class="primary-button" @click="finish">Next: how do you feel now?</button>
      </div>
    </section>

    <!-- Your messages to this tree (US7.3) -->
    <div v-if="posted.length" class="my-messages">
      <span class="eyebrow">YOUR MESSAGES TO THIS TREE</span>
      <ul>
        <li v-for="item in posted" :key="item.id">
          <span class="tag" :class="item.kind === 'damage_report' ? 'report-tag' : ''">
            {{ item.kind === 'damage_report' ? 'DAMAGE REPORT' : 'MESSAGE' }}
          </span>
          {{ item.body }} <small>{{ item.at }}</small>
        </li>
      </ul>
    </div>

    <button v-if="stage !== 'posted'" type="button" class="text-button skip" @click="finish">
      Skip to how you feel now
    </button>
  </div>
</template>

<style scoped>
.pin-flow {
  display: grid;
  gap: 14px;
}
.sprout-line {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.45;
  color: var(--tg-green-950);
  font-weight: 600;
}
.pin-card {
  border: 1px solid var(--tg-border);
  border-radius: 14px;
  padding: 12px 14px;
  display: grid;
  gap: 4px;
}
.eyebrow {
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: var(--tg-green-700);
}
.coords {
  margin: 0;
  font-weight: 700;
}
.accuracy {
  margin: 0;
  font-size: 0.8rem;
  color: var(--tg-muted);
}
.pin-step {
  display: grid;
  gap: 14px;
  justify-items: stretch;
}
.pin-step > .primary-button {
  width: 100%;
  min-height: 52px;
}
.pin-step h2 {
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.5rem;
  margin: 0;
}
.pin-note {
  margin: 0;
  color: #6b766a;
  font-size: 0.9rem;
  line-height: 1.45;
}
.pinned-actions {
  flex-wrap: wrap;
}
.pin-thumb-img {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  object-fit: cover;
  flex-shrink: 0;
}
.chips-row {
  margin: 10px 0 14px;
}
.pin-photo {
  width: 100%;
  max-height: 220px;
  object-fit: cover;
  border-radius: 12px;
  margin-top: 6px;
}
.row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.weak {
  border: 1px solid #e9b98a;
  background: #fff6ec;
  border-radius: 12px;
  padding: 10px 12px;
  color: #8a4a12;
  font-size: 0.85rem;
}
.field-label {
  display: block;
  margin: 14px 0 6px;
  font-weight: 700;
  font-size: 0.85rem;
}
textarea {
  width: 100%;
  border: 1.5px solid var(--tg-border);
  border-radius: 12px;
  padding: 10px 12px;
  font: inherit;
  resize: vertical;
}
.pin-summary {
  display: flex;
  gap: 12px;
  align-items: center;
  background: #eef5ea;
  border-radius: 14px;
  padding: 10px 12px;
  font-size: 0.86rem;
}
.pin-summary small {
  display: block;
  color: #6b766a;
}
.pin-thumb {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #d9ead0;
  flex-shrink: 0;
}
.saved-note {
  font-size: 0.75rem;
  color: var(--tg-muted);
  margin: 4px 0 0;
}
.chip {
  border: 1px solid var(--tg-green-100);
  background: var(--tg-green-50);
  color: var(--tg-green-900);
  border-radius: 999px;
  padding: 6px 12px;
  font-weight: 700;
  font-size: 0.8rem;
  cursor: pointer;
}
.report {
  border: 1.5px solid #e9b98a;
  border-radius: 14px;
  padding: 14px;
  display: grid;
  gap: 10px;
}
.report h3 {
  margin: 0;
  font-size: 1rem;
}
.report dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 6px 14px;
  margin: 0;
  font-size: 0.85rem;
}
.report dt {
  font-weight: 700;
  color: var(--tg-muted);
}
.report dd {
  margin: 0;
}
.my-messages ul {
  list-style: none;
  padding: 0;
  margin: 6px 0 0;
  display: grid;
  gap: 8px;
}
.my-messages li {
  font-size: 0.88rem;
  border-bottom: 1px solid var(--tg-border);
  padding-bottom: 8px;
}
.my-messages small {
  color: var(--tg-muted);
}
.tag {
  display: inline-block;
  font-size: 0.66rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  background: var(--tg-green-100);
  color: var(--tg-green-900);
  border-radius: 6px;
  padding: 2px 6px;
  margin-right: 6px;
}
.tag.report-tag {
  background: #f7d9c4;
  color: #8a4a12;
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
}
.primary-button {
  background: var(--tg-green-800);
  color: white;
  border: none;
}
.primary-button:disabled,
.ghost-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  font-size: 0.82rem;
  cursor: pointer;
  justify-self: start;
  padding: 0;
}
.skip {
  color: var(--tg-muted);
}
.form-error {
  color: #b44235;
  font-size: 0.82rem;
}
</style>
