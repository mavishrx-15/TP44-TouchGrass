<script setup lang="ts">
import { computed } from 'vue'
import { RefreshLeft } from '@element-plus/icons-vue'
import type { DensityTier, TreeGenus } from '@/types/discovery'

const densities = defineModel<DensityTier[]>('densities', { required: true })
const genera = defineModel<TreeGenus[]>('genera', { required: true })

defineEmits<{ reset: [] }>()

const densityOptions: DensityTier[] = ['High', 'Medium', 'Low']
defineProps<{ genusOptions: TreeGenus[] }>()

const allDensitiesOn = computed(() => densities.value.length === densityOptions.length)

function toggleAllDensities() {
  densities.value = allDensitiesOn.value ? [] : [...densityOptions]
}
</script>

<template>
  <aside class="filter-panel" aria-label="Map filters">
    <div class="panel-heading">
      <span>Map filters</span>
      <button
        type="button"
        class="density-toggle"
        :class="{ 'is-off': !allDensitiesOn }"
        :aria-pressed="allDensitiesOn"
        @click="toggleAllDensities"
      >
        Tree Density
      </button>
    </div>

    <div class="filter-group">
      <h2>Density</h2>
      <ElCheckboxGroup v-model="densities">
        <ElCheckbox v-for="tier in densityOptions" :key="tier" :value="tier">
          {{ tier }}
        </ElCheckbox>
      </ElCheckboxGroup>
    </div>

    <div class="filter-group species-group">
      <h2>Species / genus</h2>
      <ElCheckboxGroup v-model="genera">
        <ElCheckbox v-for="genus in genusOptions" :key="genus" :value="genus">
          <span class="legend-dot" :class="`genus-${genus.toLowerCase()}`" />{{ genus }}
        </ElCheckbox>
      </ElCheckboxGroup>
    </div>

    <ElButton class="reset-button" plain :icon="RefreshLeft" @click="$emit('reset')">
      Reset filters
    </ElButton>
  </aside>
</template>

<style scoped>
.filter-panel {
  position: absolute;
  z-index: 8;
  top: 22px;
  left: 22px;
  width: 208px;
  max-height: calc(100% - 44px);
  overflow-y: auto;
  padding: 16px;
  border: 1px solid rgb(23 53 29 / 10%);
  border-radius: 14px;
  background: rgb(255 255 255 / 96%);
  box-shadow: 0 8px 28px rgb(31 68 35 / 14%);
}

.panel-heading {
  display: grid;
  gap: 8px;
}

.panel-heading span,
.filter-group h2 {
  margin: 0;
  color: var(--tg-muted);
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

.density-toggle {
  padding: 11px 12px;
  border: 0;
  border-radius: 8px;
  background: var(--tg-green-700);
  color: white;
  font-family: inherit;
  font-size: 0.78rem;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.density-toggle:hover {
  background: var(--tg-green-800);
}

.density-toggle.is-off {
  background: #c3c9bd;
  color: var(--tg-muted);
}

.filter-group {
  padding: 15px 0;
  border-bottom: 1px solid rgb(23 53 29 / 10%);
}

.filter-group h2 {
  margin-bottom: 9px;
}

.filter-group :deep(.el-checkbox-group) {
  display: grid;
  gap: 2px;
}

.filter-group :deep(.el-checkbox) {
  height: 24px;
  margin-right: 0;
}

.filter-group :deep(.el-checkbox__label) {
  display: inline-flex;
  align-items: center;
  padding-left: 7px;
  color: var(--tg-text);
  font-size: 0.7rem;
}

.legend-dot {
  width: 9px;
  height: 9px;
  margin-right: 6px;
  border: 1px solid white;
  border-radius: 50%;
  background: #8c8065;
  box-shadow: 0 0 0 1px rgb(23 53 29 / 20%);
}

.genus-eucalyptus,
.genus-corymbia {
  background: #31854a;
}

.genus-acacia {
  background: #d6a52b;
}

.genus-ulmus {
  background: #7655b6;
}

.genus-platanus {
  background: #337dcc;
}

.genus-allocasuarina,
.genus-casuarina {
  background: #9b8b67;
}

.genus-quercus {
  background: #bd62ad;
}

.reset-button {
  width: 100%;
  margin-top: 14px;
}

@media (max-width: 720px) {
  .filter-panel {
    top: 76px;
    left: 12px;
    width: 178px;
    max-height: calc(100% - 92px);
    padding: 12px;
  }

  .species-group {
    display: none;
  }
}
</style>
