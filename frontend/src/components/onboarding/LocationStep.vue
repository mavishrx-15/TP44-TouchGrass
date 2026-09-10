<script setup lang="ts">
import { ref } from 'vue'
import { Location, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getPlaceDetails, getPlaceSuggestions } from '@/services/discovery.service'
import type { Coordinates } from '@/types/discovery'

const emit = defineEmits<{
  located: [coordinates: Coordinates, label: string, method: 'current' | 'search']
  back: []
}>()

interface Suggestion {
  value: string
  id: string
}

const mode = ref<'choose' | 'search'>('choose')
const locating = ref(false)
const resolving = ref(false)
const query = ref('')

function useMyLocation() {
  if (!('geolocation' in navigator)) {
    ElMessage.warning('This browser cannot share your location. Try entering an address instead.')
    mode.value = 'search'
    return
  }

  locating.value = true
  navigator.geolocation.getCurrentPosition(
    (position) => {
      locating.value = false
      emit(
        'located',
        { lat: position.coords.latitude, lng: position.coords.longitude },
        'Your current location',
        'current',
      )
    },
    () => {
      locating.value = false
      ElMessage.warning('Location access was blocked. Try entering an address instead.')
      mode.value = 'search'
    },
    { enableHighAccuracy: true, timeout: 8000 },
  )
}

async function suggest(input: string, callback: (items: Suggestion[]) => void) {
  const trimmed = input.trim()
  if (trimmed.length < 2) {
    callback([])
    return
  }
  try {
    const suggestions = await getPlaceSuggestions(trimmed)
    callback(suggestions.map((item) => ({ value: item.label, id: item.id })))
  } catch {
    // Places lookups are best-effort while typing; a failed request should
    // just show no suggestions rather than an error banner mid-keystroke.
    callback([])
  }
}

async function selectPlace(item: Suggestion) {
  if (!item.id) return
  resolving.value = true
  try {
    const place = await getPlaceDetails(item.id)
    emit('located', place.coordinates, place.label, 'search')
  } catch {
    ElMessage.error('That address could not be found. Try another search.')
  } finally {
    resolving.value = false
  }
}

function goBack() {
  if (mode.value === 'search') {
    mode.value = 'choose'
    return
  }
  emit('back')
}
</script>

<template>
  <section class="question-step">
    <div class="question-card">
      <p class="question-title">Let us get to know you</p>
      <h1 class="question-text">Where do you want to start?</h1>

      <div v-if="mode === 'choose'" class="choice-grid">
        <button type="button" class="choice-chip" :disabled="locating" @click="useMyLocation">
          <ElIcon><Location /></ElIcon>
          <span>{{ locating ? 'Finding you…' : 'Use my location' }}</span>
        </button>
        <button type="button" class="choice-chip" @click="mode = 'search'">
          <ElIcon><Search /></ElIcon>
          <span>Enter a location</span>
        </button>
      </div>

      <form v-else class="search-form" @submit.prevent>
        <label class="sr-only" for="start-location">Enter an address in the Melbourne CBD</label>
        <ElAutocomplete
          id="start-location"
          v-model="query"
          :fetch-suggestions="suggest"
          :prefix-icon="Search"
          placeholder="Search an address in the Melbourne CBD"
          :loading="resolving"
          clearable
          @select="selectPlace"
        />
      </form>

      <div class="question-actions">
        <button type="button" class="link-button" @click="goBack">Back</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.question-step {
  display: flex;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--tg-cream);
}

.question-card {
  width: min(440px, 100%);
  padding: 40px 32px;
  border: 1px solid var(--tg-border);
  border-radius: 20px;
  background: var(--tg-surface);
  text-align: center;
}

.question-title {
  margin: 0 0 14px;
  color: var(--tg-green-700);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.question-text {
  margin: 0 0 28px;
  color: var(--tg-green-950);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: clamp(1.5rem, 4vw, 1.9rem);
  line-height: 1.3;
}

.choice-grid {
  display: grid;
  gap: 10px;
}

.choice-chip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px 18px;
  border: 1.5px solid var(--tg-green-500);
  border-radius: 12px;
  background: transparent;
  color: var(--tg-text);
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition:
    background 140ms ease,
    color 140ms ease;
}

.choice-chip:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.choice-chip:not(:disabled):hover,
.choice-chip:not(:disabled):focus-visible {
  background: var(--tg-green-700);
  border-color: var(--tg-green-700);
  color: white;
}

.search-form {
  margin-top: 4px;
}

.search-form :deep(.el-input__wrapper) {
  border-radius: 11px;
  box-shadow: none;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.question-actions {
  display: flex;
  justify-content: flex-start;
  margin-top: 26px;
}

.link-button {
  padding: 8px 4px;
  border: none;
  background: none;
  color: var(--tg-muted);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}

.link-button:hover,
.link-button:focus-visible {
  color: var(--tg-text);
}
</style>
