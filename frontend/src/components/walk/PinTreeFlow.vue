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
import {
  downloadReport,
  downloadReportPhoto,
  reportFiles,
  type TreeReport,
} from '@/services/report'

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
let lastFix: GeolocationPosition | null = null
const coordinates = ref<{ lat: number; lng: number } | null>(null)
const photoUrl = ref<string | null>(null)
const photoError = ref('')
const photoSaving = ref(false)
const body = ref('')
const sending = ref(false)
const sendError = ref('')
const lastPosted = ref<string>('')
const posted = ref<{ id: string; kind: CareMessage['kind']; body: string; at: string }[]>([])
const savedReport = ref<TreeReport | null>(null)
const shareNote = ref('')
const sharing = ref(false)

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
  if (pinning.value) return
  pinning.value = true
  pinError.value = ''
  try {
    const fix = allowWeak && lastFix ? lastFix : await readPosition()
    lastFix = fix
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
  if (!pin.value || photoSaving.value) return
  photoSaving.value = true
  photoError.value = ''
  try {
    const updated = await updatePinPhoto(pin.value.id, dataUrl)
    pin.value = updated
    photoUrl.value = dataUrl
    stage.value = 'message'
    lastPosted.value = PHOTO_DONE
  } catch (e) {
    photoError.value = friendlyError(e, 'The photo could not be saved.')
  } finally {
    photoSaving.value = false
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
  if (!pin.value || sending.value) return
  sending.value = true
  sendError.value = ''
  try {
    const message = await postMessage(pin.value.id, body.value.trim(), kind)
    posted.value = [
      {
        id: message.id,
        kind,
        body: message.body,
        at: new Date().toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit' }),
      },
      ...posted.value,
    ]
    if (kind === 'damage_report') {
      savedReport.value = {
        body: body.value.trim(),
        location: coordinates.value
          ? `${coordinates.value.lat.toFixed(5)}, ${coordinates.value.lng.toFixed(5)} (near ${props.landmark})`
          : props.landmark,
        date: new Date().toLocaleDateString('en-AU'),
        photoDataUrl: photoUrl.value,
      }
      shareNote.value = ''
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
  if (!savedReport.value || sharing.value) return
  sharing.value = true
  try {
    const files = reportFiles(savedReport.value)
    if (navigator.share && navigator.canShare?.({ files })) {
      await navigator.share({ title: 'Possible tree damage report', files })
      shareNote.value = 'Report handed to your chosen app. Complete sending there.'
    } else {
      downloadReport(savedReport.value)
      shareNote.value =
        'Downloaded your report with its photo. You can also save the photo for the council form.'
    }
  } catch (error) {
    shareNote.value =
      error instanceof Error && error.name === 'AbortError'
        ? 'Sharing cancelled. Your report is still saved in TouchGrass.'
        : 'Sharing is unavailable here. Download your report instead.'
  } finally {
    sharing.value = false
  }
}

function startAnother() {
  body.value = ''
  savedReport.value = null
  shareNote.value = ''
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
      <span class="eyebrow">A LITTLE CONNECTION</span>
      <h2>Pin the tree you’re with</h2>
      <p class="pin-note">
        Stand next to your tree. I’ll drop a pin at your live location, then you can snap a photo.
      </p>
      <button type="button" class="primary-button" :disabled="pinning" @click="dropPin()">
        <ElIcon><LocationIcon /></ElIcon
        >{{ pinning ? 'Finding your position…' : 'Drop a pin here' }}
      </button>
      <div v-if="weakSignal" class="weak" role="alert">
        <p>
          <ElIcon><Warning /></ElIcon> {{ PIN_WARNING }} (accuracy about {{ liveAccuracy }} m)
        </p>
        <div class="row">
          <button type="button" class="ghost-button" :disabled="pinning" @click="dropPin()">
            Wait and try again
          </button>
          <button type="button" class="text-button" :disabled="pinning" @click="dropPin(true)">
            Pin it anyway
          </button>
        </div>
      </div>
      <p v-if="pinError" class="form-error" role="alert">{{ pinError }}</p>
    </section>

    <!-- The pin card, shown once a pin exists -->
    <div v-if="pin" class="pin-card">
      <div class="pin-card-heading">
        <img v-if="photoUrl" :src="photoUrl" alt="Your pinned tree" class="pin-thumb-img" />
        <span v-else class="pin-status-icon"
          ><ElIcon><LocationIcon /></ElIcon
        ></span>
        <div>
          <span class="eyebrow">YOUR TREE PIN</span><strong>One tree. Your little moment.</strong>
          <p class="accuracy">
            {{
              pin.accuracyM > WEAK_GPS_ACCURACY_M ? 'Approximate location saved' : 'Location saved'
            }}{{ photoUrl ? ' · Photo attached' : '' }}
          </p>
        </div>
      </div>
      <details class="location-details">
        <summary>Location details</summary>
        <p class="coords">{{ pin.latitude.toFixed(5) }}, {{ pin.longitude.toFixed(5) }}</p>
        <p class="accuracy">GPS accuracy: about {{ Math.round(pin.accuracyM) }} m.</p>
      </details>
    </div>

    <!-- Pinned: the prototype's three choices -->
    <section v-if="stage === 'pinned'" class="pinned-actions flow-card">
      <h2>Make this moment yours</h2>
      <p class="pin-note">Keep a photo, leave a few kind words, or simply enjoy being here.</p>
      <button type="button" class="primary-button" @click="stage = 'photo'">
        Take a photo of your tree
      </button>
      <button type="button" class="ghost-button" @click="stage = 'message'">Write a message</button>
      <button type="button" class="text-button" @click="finish">Not now</button>
    </section>

    <!-- US7.2 Photo -->
    <section v-if="stage === 'photo'" class="photo-step">
      <div class="section-heading">
        <span class="eyebrow">A MOMENT TO KEEP</span>
        <h2>Your tree, through your eyes</h2>
        <p class="pin-note">Include the trunk and canopy if you can. A photo is optional.</p>
      </div>
      <CameraCapture
        :saving="photoSaving"
        @captured="onPhoto"
        @cancel="(skipPhoto) => (stage = skipPhoto || photoUrl ? 'message' : 'pinned')"
      />
      <p v-if="photoSaving" class="pin-note" role="status">Saving your photo…</p>
      <p v-if="photoError" class="form-error" role="alert">{{ photoError }}</p>
    </section>

    <!-- US7.3 / US7.4 Message and report -->
    <section v-if="stage === 'message' || stage === 'report'" class="message-step">
      <div v-if="stage === 'message'" class="compose-card flow-card">
        <span class="eyebrow">A FEW WORDS GO A LONG WAY</span>
        <h2>Leave a note for your tree</h2>
        <label class="field-label" for="tree-message">Your message to this tree</label>
        <textarea
          id="tree-message"
          v-model="body"
          :maxlength="MAX_BODY"
          rows="4"
          placeholder="Say thanks, or tell us what you see"
          aria-describedby="message-count"
        />
        <span id="message-count" class="message-count">{{ body.length }} / {{ MAX_BODY }}</span>
        <div class="row chips-row">
          <button type="button" class="chip" @click="addChip(THANKS_CHIP)">
            + {{ THANKS_CHIP }}
          </button>
          <button type="button" class="chip" @click="addChip(DAMAGE_CHIP)">
            + {{ DAMAGE_CHIP }}
          </button>
        </div>
        <button
          v-if="!photoUrl"
          type="button"
          class="text-button add-photo"
          @click="stage = 'photo'"
        >
          + Add a photo
        </button>
        <div class="row">
          <button
            type="button"
            class="primary-button"
            :disabled="!body.trim() || sending"
            @click="reviewOrPost"
          >
            {{ damageWord ? 'Review damage report' : 'Post message to this tree' }}
          </button>
        </div>
        <p class="saved-note">{{ SAVED_NOTE }}</p>
      </div>

      <!-- Damage report preview: nothing is sent until a button is tapped -->
      <div v-else class="report">
        <span class="eyebrow">REVIEW BEFORE SAVING</span>
        <h3>Damage report preview</h3>
        <p class="pin-note">A small observation can help someone care for this tree.</p>
        <blockquote class="report-description">{{ body }}</blockquote>
        <dl>
          <dt>Walk area</dt>
          <dd>{{ landmark }}</dd>
          <dt>Photo attached</dt>
          <dd>{{ photoUrl ? 'Yes' : 'No' }}</dd>
          <dt>Date</dt>
          <dd>{{ new Date().toLocaleDateString('en-AU') }}</dd>
        </dl>
        <div class="row">
          <button
            type="button"
            class="primary-button"
            :disabled="sending"
            @click="sendMessage('damage_report')"
          >
            Save damage report{{ photoUrl ? ' with photo' : '' }}
          </button>
          <button
            type="button"
            class="ghost-button"
            :disabled="sending"
            @click="sendMessage('message')"
          >
            Just post it as a message
          </button>
          <button type="button" class="text-button" @click="stage = 'message'">Edit</button>
        </div>
      </div>
      <p v-if="sendError" class="form-error" role="alert">{{ sendError }}</p>
    </section>

    <!-- Posted -->
    <section v-if="stage === 'posted'" class="posted-step">
      <div v-if="savedReport" class="report-handoff">
        <span class="success-mark" aria-hidden="true">✓</span>
        <span class="eyebrow">A LITTLE CARE MAKES A DIFFERENCE</span>
        <h3>Your report is ready</h3>
        <p>
          Saved with your pin{{ savedReport.photoDataUrl ? ' and photo' : '' }}. Thank you for
          noticing. It can appear on the map after review.
        </p>
        <details class="handoff-details">
          <summary>Send a copy to the council</summary>
          <p>
            Submit it through the council's tree maintenance page. Sharing or downloading here does
            not send it to the council.
          </p>
          <a
            class="council-link"
            href="https://www.melbourne.vic.gov.au/community/greening-the-city/tree-protection-management/Pages/tree-protection-and-management.aspx"
            target="_blank"
            rel="noopener noreferrer"
            >Report a tree to City of Melbourne ↗</a
          >
          <div class="row">
            <button type="button" class="primary-button" :disabled="sharing" @click="shareReport">
              {{ sharing ? 'Sharing…' : 'Share report' }}
            </button>
            <button type="button" class="ghost-button" @click="downloadReport(savedReport)">
              Download report
            </button>
            <button
              v-if="savedReport.photoDataUrl"
              type="button"
              class="ghost-button"
              @click="downloadReportPhoto(savedReport)"
            >
              Save photo
            </button>
          </div>
          <p v-if="shareNote" role="status">{{ shareNote }}</p>
        </details>
      </div>
      <div v-else class="message-success flow-card">
        <span class="success-mark" aria-hidden="true">✓</span>
        <h2>A little kindness, saved.</h2>
        <p class="pin-note">
          Your note is attached to this tree. It can appear on the map after review.
        </p>
      </div>
      <div class="row posted-actions">
        <button type="button" class="ghost-button" @click="startAnother">
          Write another message
        </button>
        <button type="button" class="primary-button" @click="finish">
          Next: how do you feel now?
        </button>
      </div>
    </section>

    <!-- Your messages to this tree (US7.3) -->
    <details v-if="posted.length" class="my-messages">
      <summary>
        Your messages to this tree <span>{{ posted.length }}</span>
      </summary>
      <ul>
        <li v-for="item in posted" :key="item.id">
          <span class="tag" :class="item.kind === 'damage_report' ? 'report-tag' : ''">
            {{ item.kind === 'damage_report' ? 'DAMAGE REPORT' : 'MESSAGE' }}
          </span>
          <p>{{ item.body }}</p>
          <small>{{ item.at }}</small>
        </li>
      </ul>
    </details>

    <button
      v-if="stage !== 'posted' && stage !== 'pinned'"
      type="button"
      class="text-button skip"
      @click="finish"
    >
      Skip to how you feel now
    </button>
  </div>
</template>

<style src="../../styles/walk-pin.css" scoped></style>
