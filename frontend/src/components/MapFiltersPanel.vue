<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Filter, RefreshLeft } from '@element-plus/icons-vue'
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

// A full panel floating open by default works on desktop, but on a phone it
// covers the address fields and anything else sharing that corner of the
// map. Start collapsed to a small toggle there instead; desktop keeps the
// panel open like before.
const expanded = ref(true)
onMounted(() => {
  if (window.matchMedia('(max-width: 760px)').matches) expanded.value = false
})
</script>

<template>
  <aside class="filter-panel" :class="{ collapsed: !expanded }" aria-label="Map filters">
    <button
      type="button"
      class="panel-toggle"
      :aria-expanded="expanded"
      aria-controls="map-filters-body"
      @click="expanded = !expanded"
    >
      <ElIcon><Filter /></ElIcon>Map filters
    </button>
    <div v-show="expanded" id="map-filters-body">
      <div class="panel-heading">
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
    </div>
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

.filter-panel.collapsed {
  width: auto;
  max-height: none;
  padding: 0;
  border: 0;
  background: none;
  box-shadow: none;
}

.panel-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid rgb(23 53 29 / 10%);
  border-radius: 20px;
  background: rgb(255 255 255 / 96%);
  color: var(--tg-green-800);
  font-family: inherit;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 8px 28px rgb(31 68 35 / 14%);
}

.filter-panel:not(.collapsed) .panel-toggle {
  margin-bottom: 10px;
}

#map-filters-body {
  overflow-y: auto;
  max-height: calc(100vh - 240px);
}

.panel-heading {
  display: grid;
  gap: 8px;
}

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

@media (max-width: 760px) {
  /* The address search card floats centred, starting a little way down the
     map - the collapsed toggle sits in the corner above it, not behind it. */
  .filter-panel.collapsed {
    top: 12px;
    left: 12px;
  }

  .filter-panel:not(.collapsed) {
    top: 76px;
    left: 12px;
    width: 178px;
    max-height: calc(100% - 92px);
    padding: 12px;
  }
}
</style>
