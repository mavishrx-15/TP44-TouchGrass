import { apiPost, ApiError } from '@/api/client'
import { pause, USE_MOCK_DATA } from './personalisation.service'

const SESSION_KEY = 'touchgrass.access.v1'
export const DEMO_PASSWORD = 'touchgrass-demo'
interface AccessSession {
  token: string
  expiresAt: number
  mock: boolean
}

export function getAccessToken(): string | null {
  try {
    const session: AccessSession = JSON.parse(sessionStorage.getItem(SESSION_KEY) ?? 'null')
    if (
      session &&
      typeof session.token === 'string' &&
      session.expiresAt > Date.now() &&
      session.mock === USE_MOCK_DATA
    )
      return session.token
    sessionStorage.removeItem(SESSION_KEY)
  } catch {
    /* Unavailable storage is handled by the access form. */
  }
  return null
}

export async function verifyAccess(password: string): Promise<void> {
  let token: string
  let expiresIn: number
  if (USE_MOCK_DATA) {
    await pause(350)
    if (password !== DEMO_PASSWORD) throw new Error('That password isn’t right. Please try again.')
    // This is a UI demo session, NOT a signed token or a security boundary.
    token = `demo-${crypto.randomUUID()}`
    expiresIn = 3600
  } else {
    try {
      const result = await apiPost<{ token: string; expiresIn: number }>('/api/access/verify', {
        password,
      })
      if (!result.token || !Number.isFinite(result.expiresIn) || result.expiresIn <= 0)
        throw new Error('Invalid access response')
      token = result.token
      expiresIn = result.expiresIn
    } catch (error) {
      if (error instanceof ApiError && [401, 403].includes(error.status))
        throw new Error('That password isn’t right. Please try again.')
      throw new Error('We couldn’t verify access right now. Please try again shortly.')
    }
  }
  try {
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({ token, expiresAt: Date.now() + expiresIn * 1000, mock: USE_MOCK_DATA }),
    )
  } catch {
    throw new Error('Allow session storage in your browser to continue.')
  }
}
