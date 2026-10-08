/**
 * A local, anonymous device identity for Epic 7's device credential system
 * (backend/app/routers/care.py). Generated once per browser and kept in
 * localStorage, not sessionStorage - the whole point is recognising the same
 * device across visits, not just this tab's session. Nothing here is sent
 * anywhere except as the deviceId/X-Device-Token on a pin or message post.
 */
const DEVICE_ID_KEY = 'touchgrass.device.id'
const DEVICE_TOKEN_KEY = 'touchgrass.device.token'

export function getDeviceId(): string {
  try {
    let id = localStorage.getItem(DEVICE_ID_KEY)
    if (!id) {
      id = crypto.randomUUID()
      localStorage.setItem(DEVICE_ID_KEY, id)
    }
    return id
  } catch {
    // Storage unavailable (private browsing, etc.) - a one-off id still lets
    // this single post succeed, it just won't be recognised as returning.
    return crypto.randomUUID()
  }
}

export function getDeviceToken(): string | null {
  try {
    return localStorage.getItem(DEVICE_TOKEN_KEY)
  } catch {
    return null
  }
}

export function saveDeviceToken(token: string): void {
  try {
    localStorage.setItem(DEVICE_TOKEN_KEY, token)
  } catch {
    /* Credential persistence is optional - it still works for this post. */
  }
}
