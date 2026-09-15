<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { getPlaceDetails, getPlaceSuggestions } from '@/services/discovery.service'
import type { PlaceSuggestion, Precinct, RoutePlace } from '@/types/discovery'
const props = withDefaults(
  defineProps<{
    label: string
    modelValue: RoutePlace | null
    precincts?: Precinct[]
    allowGeolocation?: boolean
  }>(),
  { precincts: () => [], allowGeolocation: false },
)
const emit = defineEmits<{ 'update:modelValue': [value: RoutePlace | null] }>()
const query = ref(props.modelValue?.label ?? '')
const open = ref(false)
const suggestions = ref<PlaceSuggestion[]>([])
const loading = ref(false)
const error = ref('')
const local = computed(() =>
  props.precincts
    .filter((p) => p.name.toLowerCase().includes(query.value.toLowerCase()))
    .slice(0, 6),
)
let timer: ReturnType<typeof setTimeout> | undefined
let controller: AbortController | undefined
let version = 0
watch(
  () => props.modelValue,
  (place) => {
    if (place) query.value = place.label
  },
)
function edit(value: string) {
  query.value = value
  emit('update:modelValue', null)
  open.value = true
  suggestions.value = []
  error.value = ''
  clearTimeout(timer)
  controller?.abort()
  const current = ++version
  loading.value = false
  if (value.trim().length < 2) return
  timer = setTimeout(async () => {
    const abort = new AbortController()
    controller = abort
    loading.value = true
    try {
      const result = await getPlaceSuggestions(value.trim(), abort.signal)
      if (current === version) suggestions.value = result
    } catch {
      if (current === version && !abort.signal.aborted)
        error.value = 'Place search is unavailable. Try a listed precinct or retry.'
    } finally {
      if (current === version) loading.value = false
    }
  }, 250)
}
function choose(place: RoutePlace) {
  ++version
  clearTimeout(timer)
  controller?.abort()
  query.value = place.label
  open.value = false
  loading.value = false
  error.value = ''
  emit('update:modelValue', place)
}
async function resolve(place: PlaceSuggestion) {
  const current = ++version
  clearTimeout(timer)
  controller?.abort()
  const abort = new AbortController()
  controller = abort
  loading.value = true
  try {
    const result = await getPlaceDetails(place.id, abort.signal)
    if (current === version) choose(result)
  } catch {
    if (current === version && !abort.signal.aborted)
      error.value = 'Could not resolve this place. Please select it again.'
  } finally {
    if (current === version) loading.value = false
  }
}
function locate() {
  if (!navigator.geolocation) {
    error.value = 'Geolocation is unavailable. Search for your location.'
    return
  }
  const current = ++version
  controller?.abort()
  clearTimeout(timer)
  loading.value = true
  navigator.geolocation.getCurrentPosition(
    (position) => {
      if (current !== version) return
      choose({
        id: 'device',
        label: 'My current location',
        coordinates: { lat: position.coords.latitude, lng: position.coords.longitude },
      })
    },
    () => {
      if (current === version) {
        loading.value = false
        error.value = 'Location permission or signal unavailable. Search for your location.'
      }
    },
    { timeout: 10000, maximumAge: 60000 },
  )
}
onBeforeUnmount(() => {
  ++version
  clearTimeout(timer)
  controller?.abort()
})
</script>
<template>
  <div class="location-search">
    <label class="field-label"
      >{{ label }}
      <ElInput
        :model-value="query"
        :placeholder="`Search ${label.toLowerCase()}`"
        clearable
        :aria-label="label"
        @update:model-value="edit(String($event))"
        @focus="open = true"
        @keydown.esc="open = false"
      />
    </label>
    <button
      v-if="allowGeolocation"
      type="button"
      class="text-action"
      :disabled="loading"
      @click="locate"
    >
      Use my current location
    </button>
    <div v-if="open" class="location-options" :aria-label="`${label} suggestions`">
      <button
        v-for="p in local"
        :key="p.id"
        type="button"
        @click="choose({ id: p.id, label: p.name, coordinates: p.referencePoint })"
      >
        {{ p.name }} <small>Precinct centre</small>
      </button>
      <button v-for="p in suggestions" :key="p.id" type="button" @click="resolve(p)">
        {{ p.label }}
      </button>
      <p v-if="loading" role="status">Finding locations…</p>
      <p v-else-if="query.length >= 2 && !local.length && !suggestions.length && !error">
        No suggestions. Try another location.
      </p>
      <button
        v-if="local.length || suggestions.length"
        type="button"
        class="text-action"
        @click="open = false"
      >
        Close suggestions
      </button>
    </div>
    <p v-if="error" role="alert" class="form-error">{{ error }}</p>
    <small v-if="query && !modelValue && !loading"
      >Select a suggestion to confirm this location.</small
    >
  </div>
</template>
<style scoped>
.location-search {
  position: relative;
}
.location-options {
  margin: 8px 0;
  border: 1px solid var(--tg-border);
  border-radius: 12px;
  max-height: 260px;
  overflow: auto;
  background: white;
}
.location-options button {
  display: block;
  width: 100%;
  text-align: left;
  border: 0;
  padding: 12px;
  background: transparent;
  cursor: pointer;
}
.location-options button:hover {
  background: var(--tg-green-50);
}
.location-options small {
  display: block;
  color: var(--tg-muted);
}
.location-options p {
  padding: 0 12px;
}
</style>
