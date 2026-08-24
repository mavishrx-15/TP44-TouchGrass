<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiGet } from '@/api/client'

// Placeholder page. It exists to prove the frontend can reach the backend;
// replace it with the first real user story view.
type Health = { status: string; service: string }

const health = ref<Health | null>(null)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    health.value = await apiGet<Health>('/health')
  } catch {
    error.value = 'Backend not reachable. Start it with: uvicorn app.main:app --reload --port 8080'
  }
})
</script>

<template>
  <section>
    <p v-if="health">Backend connected — {{ health.service }} is {{ health.status }}.</p>
    <p v-else-if="error">{{ error }}</p>
    <p v-else>Checking the backend…</p>
  </section>
</template>
