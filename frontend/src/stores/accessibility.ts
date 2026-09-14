import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

const STORAGE_KEY = 'touchgrass.blindmode.v1'

function hasSpeechSynthesis(): boolean {
  return (
    typeof window !== 'undefined' &&
    'speechSynthesis' in window &&
    typeof SpeechSynthesisUtterance !== 'undefined'
  )
}

// Blind mode: a visible, user-toggled preference that reads key updates aloud
// via the browser's built-in speech synthesis. This is additive to the ARIA/
// screen-reader support already in the markup - it does not replace it, and
// works even for sighted users who just want audio confirmation.
export const useAccessibilityStore = defineStore('accessibility', () => {
  const blindMode = ref(
    (() => {
      try {
        return localStorage.getItem(STORAGE_KEY) === 'true'
      } catch {
        return false
      }
    })(),
  )
  const supported = hasSpeechSynthesis()

  function toggle() {
    blindMode.value = !blindMode.value
  }

  watch(blindMode, (value) => {
    try {
      localStorage.setItem(STORAGE_KEY, String(value))
    } catch {
      /* Storage unavailable; the toggle still works for this page load. */
    }
    if (!value && supported) window.speechSynthesis.cancel()
  })

  function speak(text: string) {
    if (!blindMode.value || !supported) return
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(text))
  }

  return { blindMode, supported, toggle, speak }
})
