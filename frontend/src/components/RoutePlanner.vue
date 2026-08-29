<script setup lang="ts">
import { Location, Search } from '@element-plus/icons-vue'
import { ref } from 'vue'
import type { RouteOption } from '@/types/discovery'

const props = defineProps<{ options: RouteOption[]; selectedId: RouteOption['id'] }>()
const emit = defineEmits<{
  select: [id: RouteOption['id']]
  close: []
}>()

const destination = ref('Tree-Dense Zone 02')

const fastest = props.options.find((route) => route.id === 'fastest')
const green = props.options.find((route) => route.id === 'green')
</script>

<template>
  <section class="route-planner" aria-label="Route planner">
    <div class="route-inputs">
      <ElInput model-value="My location" :prefix-icon="Location" readonly />
      <ElInput v-model="destination" :prefix-icon="Search" placeholder="Enter a destination" />
    </div>

    <div class="route-options">
      <button
        v-for="option in options"
        :key="option.id"
        class="route-option"
        :class="{ selected: selectedId === option.id }"
        type="button"
        @click="emit('select', option.id)"
      >
        <span class="route-symbol" aria-hidden="true">{{ option.id === 'green' ? '♧' : '↯' }}</span>
        <span>
          <strong>{{ option.label }}</strong>
          <small>
            {{ option.durationMinutes }} min · {{ option.distanceKm.toFixed(1) }} km ·
            {{ option.treeCount }} trees
          </small>
        </span>
        <b v-if="selectedId === option.id">Selected</b>
      </button>
    </div>

    <p v-if="fastest && green" class="comparison">
      Green Path passes {{ green.treeCount - fastest.treeCount }} more trees, only
      {{ green.durationMinutes - fastest.durationMinutes }} min longer.
    </p>
    <ElButton class="close-button" text @click="emit('close')">Close directions</ElButton>
  </section>
</template>

<style scoped>
.route-planner {
  position: absolute;
  z-index: 9;
  top: 22px;
  left: 50%;
  width: min(420px, calc(100% - 480px));
  padding: 14px;
  border: 1px solid rgb(23 53 29 / 10%);
  border-radius: 15px;
  background: rgb(255 255 255 / 97%);
  box-shadow: 0 10px 30px rgb(31 68 35 / 16%);
  transform: translateX(-50%);
}

.route-inputs {
  display: grid;
  grid-template-columns: 0.8fr 1.2fr;
  gap: 8px;
}

.route-options {
  display: grid;
  gap: 7px;
  margin-top: 10px;
}

.route-option {
  display: grid;
  width: 100%;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--tg-border);
  border-radius: 9px;
  background: white;
  color: var(--tg-text);
  text-align: left;
  cursor: pointer;
}

.route-option.selected {
  border-color: var(--tg-green-700);
  background: var(--tg-green-50);
}

.route-symbol {
  color: var(--tg-green-700);
  font-size: 1.1rem;
}

.route-option strong,
.route-option small {
  display: block;
}

.route-option strong {
  color: var(--tg-green-800);
  font-size: 0.78rem;
}

.route-option small {
  margin-top: 3px;
  color: var(--tg-muted);
  font-size: 0.65rem;
}

.route-option b {
  color: var(--tg-green-700);
  font-size: 0.65rem;
}

.comparison {
  margin: 10px 0 0;
  color: var(--tg-green-700);
  font-size: 0.68rem;
  font-weight: 700;
  text-align: center;
}

.close-button {
  display: flex;
  margin: 5px auto -6px;
  font-size: 0.68rem;
}

@media (max-width: 900px) {
  .route-planner {
    right: 12px;
    left: auto;
    width: min(390px, calc(100% - 214px));
    transform: none;
  }
}

@media (max-width: 720px) {
  .route-planner {
    top: 10px;
    width: calc(100% - 24px);
  }

  .route-options,
  .comparison,
  .close-button {
    display: none;
  }
}
</style>
