<script setup lang="ts">
import { USE_MOCK_DATA } from '@/services/personalisation.service'
</script>
<template>
  <div v-if="USE_MOCK_DATA" class="demo-notice" role="note">
    <span aria-hidden="true">◌</span> Interactive preview · Sample areas and routes, not live
    navigation.
  </div>
</template>
<style scoped>
.demo-notice {
  padding: 8px 18px;
  text-align: center;
  background: #f3edda;
  color: #74602c;
  font-size: 0.72rem;
  line-height: 1.5;
  border-bottom: 1px solid #e9dfbd;
}
.demo-notice span {
  margin-right: 5px;
}
</style>
