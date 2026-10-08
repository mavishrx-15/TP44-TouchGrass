<script setup lang="ts">
import { SPROUT_SKINS, isSkinId } from '@/data/sproutSkins'
import { useRewardsStore } from '@/stores/rewards'
const rewards = useRewardsStore()
function change(event: Event) {
  const id = (event.target as HTMLSelectElement).value
  if (isSkinId(id)) rewards.wear(id)
}
</script>
<template>
  <label class="look-picker"
    >Sprout’s look
    <select :value="rewards.equippedSkin" @change="change">
      <option
        v-for="skin in SPROUT_SKINS"
        :key="skin.id"
        :value="skin.id"
        :disabled="!rewards.ownedSkins.includes(skin.id)"
      >
        {{ skin.name }}{{ rewards.ownedSkins.includes(skin.id) ? '' : ' · locked' }}
      </option>
    </select>
  </label>
</template>
<style scoped>
.look-picker {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #637357;
  font-size: 0.72rem;
  flex-wrap: wrap;
}
select {
  border: 1px solid #d9dfce;
  border-radius: 9px;
  padding: 7px 8px;
  background: #fffdf8;
  color: #254d2a;
  font: inherit;
  max-width: 170px;
}
</style>
