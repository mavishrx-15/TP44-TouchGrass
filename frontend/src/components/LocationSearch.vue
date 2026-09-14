<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { Location, Search } from '@element-plus/icons-vue'
import { resolveLocation, searchLocations } from '@/services/personalisation.service'
import type { Precinct, RoutePlace } from '@/types/discovery'

const props = withDefaults(
  defineProps<{
    modelValue: RoutePlace | null
    precincts: Precinct[]
    label?: string
    placeholder?: string
    invalid?: boolean
  }>(),
  { label: 'Starting location', placeholder: 'e.g. 123 Flinders St, or Kensington' },
)
const emit = defineEmits<{ 'update:modelValue': [value: RoutePlace | null] }>()
const query = ref(props.modelValue?.label ?? '')
const error = ref('')
const resolving = ref(false)
const input = ref<{ focus: () => void } | null>(null)
let controller: AbortController | null = null
let generation = 0
watch(
  () => props.modelValue,
  (value) => {
    if (value) query.value = value.label
  },
)
type Suggestion = { value: string; id: string; kind: 'precinct' | 'place'; place?: RoutePlace }
async function suggestions(text: string, callback: (items: Suggestion[]) => void) {
  controller?.abort()
  const current = new AbortController()
  controller = current
  const normalized = text.trim().toLowerCase()
  if (normalized.length < 2) {
    callback([])
    return
  }
  const nearby: Suggestion[] = props.precincts
    .filter((p) => p.name.toLowerCase().includes(normalized))
    .map((p) => ({
      value: p.name,
      id: p.id,
      kind: 'precinct',
      place: { id: p.id, label: p.name, coordinates: p.referencePoint },
    }))
  try {
    const places = await searchLocations(text, current.signal)
    if (!current.signal.aborted)
      callback([
        ...nearby,
        ...places.map((p) => ({ value: p.label, id: p.id, kind: 'place' as const })),
      ])
  } catch {
    if (!current.signal.aborted) {
      error.value = 'Address search is unavailable. Try a listed area instead.'
      callback(nearby)
    }
  }
}
function edit() {
  generation++
  resolving.value = false
  error.value = ''
  emit('update:modelValue', null)
}
async function choose(item: Record<string, unknown>) {
  const candidate = item as Suggestion
  const current = ++generation
  resolving.value = true
  error.value = ''
  try {
    const place = candidate.place ?? (await resolveLocation(candidate.id))
    if (current === generation) {
      emit('update:modelValue', place)
      query.value = place.label
    }
  } catch {
    if (current === generation)
      error.value = 'That location could not be resolved. Please select another result.'
  } finally {
    if (current === generation) resolving.value = false
  }
}
onBeforeUnmount(() => {
  generation++
  controller?.abort()
})
defineExpose({ focus: () => input.value?.focus() })
</script>
<template>
  <div class="location-search" :class="{ invalid }">
    <ElAutocomplete
      ref="input"
      v-model="query"
      :fetch-suggestions="suggestions"
      :debounce="250"
      :trigger-on-focus="false"
      :prefix-icon="Search"
      :aria-label="label"
      :placeholder="placeholder"
      clearable
      :aria-invalid="invalid"
      @input="edit"
      @clear="edit"
      @select="choose"
    >
      <template #default="{ item }"
        ><div class="location-suggestion">
          <ElIcon><Location /></ElIcon
          ><span
            >{{ item.value
            }}<small>{{ item.kind === 'precinct' ? 'Covered area' : 'Address' }}</small></span
          >
        </div></template
      >
    </ElAutocomplete>
    <small v-if="resolving" role="status">Finding that location…</small>
    <small v-if="error" class="form-error" role="alert">{{ error }}</small>
  </div>
</template>
<style scoped>
.location-search {
  width: 100%;
  min-width: 0;
}
.location-search :deep(.el-autocomplete) {
  display: block;
  width: 100%;
}
.location-search :deep(.el-input__wrapper) {
  min-height: 46px;
  background: var(--tg-cream);
  box-shadow: 0 0 0 1px var(--tg-border) inset;
  border-radius: 10px;
  padding: 0 14px;
}
.location-search.invalid :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #b44235 inset;
}
.location-search > small {
  display: block;
  margin-top: 7px;
}
.location-suggestion {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  max-width: 75vw;
  white-space: normal;
  line-height: 1.5;
}
.location-suggestion small {
  display: block;
  color: var(--tg-muted);
}
</style>
