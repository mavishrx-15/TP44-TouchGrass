<script setup lang="ts">
import { Search } from '@element-plus/icons-vue'
import { ref, watch } from 'vue'

const emit = defineEmits<{ explore: [suburb: string]; back: [] }>()
const props = defineProps<{ initialValue: string; precincts: string[] }>()
const suburb = ref(props.initialValue)

watch(
  () => props.initialValue,
  (value) => (suburb.value = value),
)

function suggest(query: string, callback: (items: { value: string }[]) => void) {
  const normalized = query.trim().toLocaleLowerCase()
  callback(
    props.precincts
      .filter((name) => name.toLocaleLowerCase().includes(normalized))
      .map((value) => ({ value })),
  )
}

function submit() {
  const value = suburb.value.trim()
  if (value) emit('explore', value)
}
</script>

<template>
  <section class="search-step">
    <div class="search-card">
      <p class="eyebrow">Almost there</p>
      <h1>Find greener places around you</h1>
      <p class="description">Enter your suburb to see the tree canopy nearby.</p>

      <form class="search-form" @submit.prevent="submit">
        <label class="sr-only" for="suburb-search">Enter your suburb</label>
        <ElAutocomplete
          id="suburb-search"
          v-model="suburb"
          :fetch-suggestions="suggest"
          size="large"
          :prefix-icon="Search"
          placeholder="Enter your suburb"
        />
        <ElButton type="primary" size="large" native-type="submit">Explore My Area</ElButton>
      </form>

      <button type="button" class="link-button" @click="emit('back')">Back</button>
    </div>
  </section>
</template>

<style scoped>
.search-step {
  display: flex;
  min-height: calc(100vh - 68px);
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--tg-cream);
}

.search-card {
  width: min(480px, 100%);
  text-align: center;
}

.eyebrow {
  margin: 0 0 12px;
  color: var(--tg-green-700);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  color: var(--tg-green-950);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: clamp(1.9rem, 5vw, 2.6rem);
  line-height: 1.15;
  letter-spacing: -0.02em;
}

.description {
  margin: 16px 0 28px;
  color: var(--tg-muted);
  font-size: 0.92rem;
}

.search-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

.search-form :deep(.el-input__wrapper) {
  border-radius: 11px;
  box-shadow: none;
}

.search-form .el-button {
  min-width: 154px;
  font-weight: 700;
}

.link-button {
  margin-top: 22px;
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

@media (max-width: 640px) {
  .search-form {
    grid-template-columns: 1fr;
  }

  .search-form .el-button {
    width: 100%;
  }
}
</style>
