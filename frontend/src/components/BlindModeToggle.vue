<script setup lang="ts">
import { Microphone } from '@element-plus/icons-vue'
import { useAccessibilityStore } from '@/stores/accessibility'

const accessibility = useAccessibilityStore()

function toggle() {
  accessibility.toggle()
  if (accessibility.blindMode) accessibility.speak('Blind mode on. Key updates will be read aloud.')
}
</script>
<template>
  <button
    type="button"
    class="blind-mode-toggle"
    :class="{ active: accessibility.blindMode }"
    :aria-pressed="accessibility.blindMode"
    :disabled="!accessibility.supported"
    :title="
      accessibility.supported
        ? 'Read key updates aloud'
        : 'Speech is not supported in this browser'
    "
    @click="toggle"
  >
    <ElIcon><Microphone /></ElIcon>
    <span>Blind mode: {{ accessibility.blindMode ? 'On' : 'Off' }}</span>
  </button>
</template>
<style scoped>
.blind-mode-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  margin-left: auto;
  padding: 0 12px;
  border: 1px solid var(--tg-border);
  border-radius: 20px;
  background: white;
  color: var(--tg-muted);
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
}
.blind-mode-toggle.active {
  background: var(--tg-green-800);
  border-color: var(--tg-green-800);
  color: white;
}
.blind-mode-toggle:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
@media (max-width: 640px) {
  .blind-mode-toggle span {
    display: none;
  }
  .blind-mode-toggle {
    padding: 0;
    width: 36px;
    justify-content: center;
  }
}
</style>
