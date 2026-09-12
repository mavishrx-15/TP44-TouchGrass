<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LeafIcon from '@/components/LeafIcon.vue'
import { DEMO_PASSWORD, verifyAccess } from '@/services/access.service'
import { MOCK_ACCESS } from '@/services/personalisation.service'
const password = ref('')
const error = ref('')
const busy = ref(false)
const input = ref<HTMLInputElement | null>(null)
const route = useRoute()
const router = useRouter()
async function unlock() {
  if (busy.value) return
  if (!password.value) {
    error.value = 'Enter the access password to continue.'
    input.value?.focus()
    return
  }
  error.value = ''
  busy.value = true
  try {
    await verifyAccess(password.value)
    password.value = ''
    const target =
      typeof route.query.redirect === 'string' &&
      route.query.redirect.startsWith('/') &&
      !route.query.redirect.startsWith('//') &&
      !route.query.redirect.startsWith('/access')
        ? route.query.redirect
        : '/'
    await router.replace(target)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Please try again.'
    input.value?.focus()
  } finally {
    busy.value = false
  }
}
onMounted(() => input.value?.focus())
</script>
<template>
  <main class="access-page">
    <div class="access-brand">
      <span><LeafIcon /></span>TouchGrass
    </div>
    <section class="access-card">
      <span class="eyebrow">A little more green awaits</span>
      <h1>Welcome to TouchGrass.</h1>
      <p>Enter the shared access password to step inside. No account needed.</p>
      <form @submit.prevent="unlock">
        <label for="access-password">Access password</label>
        <input
          id="access-password"
          ref="input"
          v-model="password"
          type="password"
          autocomplete="current-password"
          :aria-invalid="!!error"
          :aria-describedby="error ? 'access-error' : undefined"
          :disabled="busy"
          @input="error = ''"
        />
        <p v-if="error" id="access-error" class="form-error" role="alert">{{ error }}</p>
        <button class="primary-button" :disabled="busy" type="submit">
          {{ busy ? 'Checking…' : 'Enter TouchGrass →' }}
        </button>
      </form>
      <p v-if="MOCK_ACCESS" class="access-demo">
        Prototype access · Use <code>{{ DEMO_PASSWORD }}</code
        ><br />This demo gate does not secure live data.
      </p>
      <small>Access is remembered in this tab for up to one hour.</small>
    </section>
    <p class="access-tagline">Small changes. A bigger impact.</p>
  </main>
</template>
<style scoped>
.access-page {
  min-height: 100svh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 36px 20px;
  background:
    radial-gradient(ellipse at 10% 90%, #dcebcf 0%, transparent 45%),
    radial-gradient(ellipse at 95% 5%, #e6f1d9 0%, transparent 40%), var(--tg-cream);
}
.access-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font:
    bold 1.5rem Georgia,
    serif;
  margin-bottom: 30px;
}
.access-brand span {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: var(--tg-green-700);
  color: white;
}
.access-brand svg {
  width: 24px;
}
.access-card {
  width: min(460px, 100%);
  background: white;
  border: 1px solid var(--tg-border);
  border-radius: 22px;
  padding: 38px;
  box-shadow: var(--tg-shadow);
}
h1 {
  font:
    bold 2rem/1.15 Georgia,
    serif;
  margin: 15px 0;
  color: var(--tg-green-950);
}
p {
  color: var(--tg-muted);
  line-height: 1.65;
  font-size: 0.9rem;
}
form {
  display: grid;
  gap: 12px;
  margin: 26px 0;
}
label {
  font-weight: 650;
  font-size: 0.9rem;
}
input {
  width: 100%;
  height: 48px;
  border-radius: 9px;
  border: 1px solid var(--tg-border);
  padding: 0 12px;
  background: var(--tg-cream);
}
.access-demo {
  background: var(--tg-warning-soft);
  color: #74602c;
  border-radius: 9px;
  padding: 12px;
  font-size: 0.8rem;
}
small {
  color: var(--tg-muted);
  font-size: 0.74rem;
}
.access-tagline {
  font-size: 0.75rem;
  margin-top: 25px;
}
@media (max-width: 400px) {
  .access-card {
    padding: 28px 22px;
  }
}
</style>
