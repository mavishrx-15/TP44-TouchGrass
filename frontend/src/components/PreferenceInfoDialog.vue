<script setup lang="ts">
defineProps<{ activeInfo: 'canopy' | 'shade' | null }>()
const emit = defineEmits<{ close: [] }>()
</script>
<template>
  <ElDialog
    :model-value="activeInfo !== null"
    :title="activeInfo === 'canopy' ? 'Tree canopy' : 'Shade'"
    width="min(520px, 92vw)"
    @update:model-value="!$event && emit('close')"
  >
    <p v-if="activeInfo === 'canopy'">
      Prioritise routes passing tree-dense zones. We use recorded tree counts to compare routes; the
      data does not measure the percentage of overhead canopy.
    </p>
    <p v-else>
      Prioritise surroundings with more park trees. Park-tree share is an estimate of opportunities
      for shade; it does not predict shadows or sunlight at a specific time.
    </p>
    <template #footer><ElButton type="primary" @click="emit('close')">Got it</ElButton></template>
  </ElDialog>
</template>
