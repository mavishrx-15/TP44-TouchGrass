<script setup lang="ts">
defineProps<{ activeInfo: 'canopy' | 'shade' | null }>()
const emit = defineEmits<{ close: [] }>()
</script>
<template>
  <ElDialog
    :model-value="activeInfo !== null"
    :title="activeInfo === 'canopy' ? 'Tree canopy' : 'Shade & thermal comfort'"
    width="min(480px, calc(100vw - 32px))"
    align-center
    @close="emit('close')"
  >
    <p class="info-pending">
      The explanatory text for this panel is awaiting the team’s approved copy.
    </p>
    <p class="info-sources">Sources: awaiting the canonical Epic 3 document.</p>
  </ElDialog>
</template>
<style scoped>
.info-pending {
  font-size: 0.95rem;
  line-height: 1.75;
  color: var(--tg-text);
}
.info-sources {
  margin-top: 24px;
  color: var(--tg-muted);
  font-size: 0.75rem;
}
</style>
