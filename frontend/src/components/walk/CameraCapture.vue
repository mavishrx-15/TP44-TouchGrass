<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Camera, Picture } from '@element-plus/icons-vue'
import { CAMERA_BLOCKED, PHOTO_GUIDE, friendlyError } from '@/data/walkMessages'
import { photoFromFile, photoFromVideo } from '@/services/photo'

/**
 * US7.2: the camera opens inside TouchGrass with the framing guide. If the
 * camera is blocked, Sprout offers the Photos picker or carrying on without one.
 */
const emit = defineEmits<{
  captured: [dataUrl: string]
  cancel: []
}>()

const video = ref<HTMLVideoElement | null>(null)
const blocked = ref(false)
const working = ref(false)
const error = ref('')
let stream: MediaStream | null = null

function stopCamera() {
  stream?.getTracks().forEach((track) => track.stop())
  stream = null
}

async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
      audio: false,
    })
    if (video.value) {
      video.value.srcObject = stream
      await video.value.play()
    }
  } catch {
    blocked.value = true
  }
}

async function takePhoto() {
  if (!video.value || working.value) return
  working.value = true
  error.value = ''
  try {
    const dataUrl = await photoFromVideo(video.value)
    stopCamera()
    emit('captured', dataUrl)
  } catch (e) {
    error.value = friendlyError(e, 'The photo could not be taken.')
  } finally {
    working.value = false
  }
}

async function pickFromPhotos(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  working.value = true
  error.value = ''
  try {
    const dataUrl = await photoFromFile(file)
    stopCamera()
    emit('captured', dataUrl)
  } catch (e) {
    error.value = friendlyError(e, 'That photo could not be used.')
  } finally {
    working.value = false
  }
}

function cancel() {
  stopCamera()
  emit('cancel')
}

onMounted(startCamera)
onBeforeUnmount(stopCamera)
</script>

<template>
  <div class="camera">
    <div v-if="!blocked" class="viewfinder">
      <video ref="video" playsinline muted aria-label="Camera preview" />
      <p class="guide">{{ PHOTO_GUIDE }}</p>
      <span class="location-tag">Location tagged</span>
    </div>
    <p v-else class="camera-blocked" role="alert">{{ CAMERA_BLOCKED }}</p>

    <p v-if="error" class="form-error" role="alert">{{ error }}</p>

    <div class="camera-actions">
      <button v-if="!blocked" type="button" class="shutter" :disabled="working" aria-label="Take photo" @click="takePhoto">
        <ElIcon><Camera /></ElIcon>
      </button>
      <label class="ghost-button photos-button">
        <ElIcon><Picture /></ElIcon> Photos
        <input type="file" accept="image/*" class="visually-hidden" @change="pickFromPhotos" />
      </label>
      <button type="button" class="text-button" @click="cancel">{{ blocked ? 'Continue without a photo' : 'Cancel' }}</button>
    </div>
  </div>
</template>

<style scoped>
.camera {
  display: grid;
  gap: 12px;
}
.viewfinder {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  background: #111;
  aspect-ratio: 4 / 3;
}
.viewfinder video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.guide {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 12px;
  margin: 0;
  text-align: center;
  color: white;
  font-weight: 700;
  text-shadow: 0 1px 4px #000a;
}
.location-tag {
  position: absolute;
  top: 10px;
  left: 10px;
  font-size: 0.72rem;
  font-weight: 700;
  color: white;
  background: #0007;
  border-radius: 999px;
  padding: 4px 9px;
}
.camera-blocked {
  font-size: 0.9rem;
  color: var(--tg-green-950);
}
.camera-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.shutter {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  border: 4px solid var(--tg-green-800);
  background: white;
  font-size: 1.3rem;
  cursor: pointer;
}
.shutter:disabled {
  opacity: 0.6;
}
.photos-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}
.ghost-button {
  background: white;
  color: var(--tg-green-800);
  border: 1.5px solid var(--tg-green-800);
  border-radius: 999px;
  padding: 10px 16px;
  font-weight: 700;
  font-size: 0.85rem;
}
.text-button {
  background: none;
  border: none;
  color: var(--tg-green-700);
  font-weight: 700;
  cursor: pointer;
}
.form-error {
  color: #b44235;
  font-size: 0.82rem;
}
</style>
