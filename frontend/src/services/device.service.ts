/**
 * A local, anonymous device identity for Epic 7's device credential system
 * (backend/app/routers/care.py). Generated once per browser and kept in
 * localStorage, not sessionStorage - the whole point is recognising the same
 * device across visits, not just this tab's session. Nothing here is sent
 * anywhere except as the deviceId/X-Device-Token on a pin or message post.
 */
const DEVICE_ID_KEY = 'touchgrass.device.id'
const DEVICE_TOKEN_KEY = 'touchgrass.device.token'
let memoryId: string | null = null
let memoryToken: string | null = null
let storageUnavailable = false

export function getDeviceId(): string {
  if (storageUnavailable) return (memoryId ??= crypto.randomUUID())
  try {
    let id = localStorage.getItem(DEVICE_ID_KEY)
    if (!id) {
      id = crypto.randomUUID()
      localStorage.setItem(DEVICE_ID_KEY, id)
    }
    memoryId = id
    return id
  } catch {
    storageUnavailable = true
    return (memoryId ??= crypto.randomUUID())
  }
}

export function getDeviceToken(): string | null {
  if (storageUnavailable) return memoryToken
  try {
    memoryToken = localStorage.getItem(DEVICE_TOKEN_KEY)
    return memoryToken
  } catch {
    storageUnavailable = true
    return memoryToken
  }
}

export function saveDeviceToken(token: string): void {
  memoryToken = token
  try {
    localStorage.setItem(DEVICE_TOKEN_KEY, token)
  } catch {
    storageUnavailable = true
  }
}

/** Start a new anonymous identity after a lost credential; existing pins stay owned by the old one. */
export function resetDeviceCredentials(): void {
  memoryId = crypto.randomUUID()
  memoryToken = null
  try {
    localStorage.setItem(DEVICE_ID_KEY, memoryId)
    localStorage.removeItem(DEVICE_TOKEN_KEY)
  } catch {
    storageUnavailable = true
  }
}
