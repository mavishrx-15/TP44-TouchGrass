<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { setAccessToken } from '@/api/client'

const router = useRouter()
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function verifyPassword() {
  submitting.value = true
  error.value = ''
  try {
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/access/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password.value }),
    })
    if (!response.ok) {
      error.value = response.status === 401 ? 'Incorrect password.' : 'Unable to verify access.'
      return
    }
    const result: { token: string } = await response.json()
    setAccessToken(result.token)
    await router.push({ name: 'home' })
  } catch {
    error.value = 'Backend not reachable.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="access-card">
    <h2>Enter password</h2>
    <p>This development build requires a password to continue.</p>
    <form @submit.prevent="verifyPassword">
      <label for="access-password">Password</label>
      <input id="access-password" v-model="password" type="password" required autofocus />
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit" :disabled="submitting">
        {{ submitting ? 'Checking…' : 'Continue' }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.access-card {
  max-width: 420px;
  margin: 80px auto;
}
form {
  display: grid;
  gap: 12px;
}
input,
button {
  font: inherit;
  padding: 10px;
}
button {
  color: white;
  background: #2f6b3f;
  border: 0;
  cursor: pointer;
}
.error {
  color: #b42318;
}
</style>
