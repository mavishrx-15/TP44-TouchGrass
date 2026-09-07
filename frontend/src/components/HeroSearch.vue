<script setup lang="ts">
import { Location, Search } from '@element-plus/icons-vue'
import { ref, watch } from 'vue'

const emit = defineEmits<{ explore: [suburb: string] }>()
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
  <section id="top" class="hero">
    <div class="hero-glow hero-glow-one" />
    <div class="hero-glow hero-glow-two" />
    <div class="page-container hero-inner">
      <div class="hero-copy">
        <p class="eyebrow">
          <ElIcon><Location /></ElIcon> Melbourne Urban Forest
        </p>
        <h1>Find greener places<br />around you.</h1>
        <p class="hero-description">
          Explore Melbourne's tree canopy, discover greener walking routes, learn about local trees,
          and help care for your neighbourhood.
        </p>

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
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(120deg, var(--tg-green-950), var(--tg-green-800));
  color: white;
}

.hero-inner {
  position: relative;
  z-index: 1;
  display: flex;
  min-height: 360px;
  align-items: center;
  padding-block: 58px;
}

.hero-copy {
  width: min(640px, 100%);
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0 0 16px;
  color: var(--tg-green-300);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: clamp(2.65rem, 6vw, 4.8rem);
  line-height: 0.98;
  letter-spacing: -0.04em;
}

.hero-description {
  max-width: 580px;
  margin: 24px 0 30px;
  color: rgb(255 255 255 / 82%);
  font-size: 1rem;
  line-height: 1.7;
}

.search-form {
  display: grid;
  max-width: 590px;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

.search-form :deep(.el-input__wrapper) {
  border-radius: 11px;
  box-shadow: none;
}

.search-form .el-button {
  min-width: 154px;
  border-color: var(--tg-green-500);
  background: var(--tg-green-500);
  font-weight: 700;
}

.hero-glow {
  position: absolute;
  border-radius: 50%;
  background: rgb(122 190 73 / 12%);
  filter: blur(1px);
}

.hero-glow-one {
  width: 380px;
  height: 380px;
  top: -210px;
  right: 8%;
}

.hero-glow-two {
  width: 280px;
  height: 280px;
  right: -90px;
  bottom: -170px;
}

@media (max-width: 640px) {
  .hero-inner {
    min-height: 430px;
    padding-block: 52px;
  }

  .search-form {
    grid-template-columns: 1fr;
  }

  .search-form .el-button {
    width: 100%;
  }
}
</style>
