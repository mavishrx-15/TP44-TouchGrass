import { apiGet, apiPost, apiPut } from '@/api/client'
import { getDeviceId, getDeviceToken, saveDeviceToken } from '@/services/device.service'

/**
 * Epic 7 API client. Matches the contract at the top of backend/app/routers/care.py.
 *
 * Every pin, photo retake and message carries this browser's deviceId and,
 * once issued, its X-Device-Token - see the DEVICE CREDENTIALS note in that
 * file. Callers never see this plumbing; createPin/updatePinPhoto/postMessage
 * read and save the credential themselves.
 */

export interface CarePin {
  id: string
  zoneId: string | null
  latitude: number
  longitude: number
  accuracyM: number
  hasPhoto: boolean
  photoStatus: 'pending' | 'approved' | 'rejected'
  createdAt: string
  deviceToken?: string | null
}

export interface CareMessage {
  id: string
  pinId: string
  zoneId: string | null
  body: string
  kind: 'message' | 'damage_report'
  status: 'pending' | 'approved' | 'rejected'
  createdAt: string
  deviceToken?: string | null
}

export interface PublicMessage {
  id: string
  body: string
  createdAt: string
  pin: { latitude: number; longitude: number }
  photoDataUrl: string | null
}

function deviceHeaders(): Record<string, string> {
  const token = getDeviceToken()
  return token ? { 'X-Device-Token': token } : {}
}

/** Saves a newly issued credential, if this post is the device's first. */
function keepAnyIssuedToken<T extends { deviceToken?: string | null }>(result: T): T {
  if (result.deviceToken) saveDeviceToken(result.deviceToken)
  return result
}

export async function createPin(input: {
  zoneId: string | null
  latitude: number
  longitude: number
  accuracyM: number
  photoDataUrl: string | null
}): Promise<CarePin> {
  const result = await apiPost<CarePin>(
    '/api/care/pins',
    { ...input, deviceId: getDeviceId() },
    undefined,
    deviceHeaders(),
  )
  return keepAnyIssuedToken(result)
}

export async function updatePinPhoto(pinId: string, photoDataUrl: string): Promise<CarePin> {
  const result = await apiPut<CarePin>(
    `/api/care/pins/${encodeURIComponent(pinId)}/photo`,
    { photoDataUrl, deviceId: getDeviceId() },
    undefined,
    deviceHeaders(),
  )
  return keepAnyIssuedToken(result)
}

export async function postMessage(
  pinId: string,
  body: string,
  kind: CareMessage['kind'] = 'message',
): Promise<CareMessage> {
  const result = await apiPost<CareMessage>(
    `/api/care/pins/${encodeURIComponent(pinId)}/messages`,
    { body, kind, deviceId: getDeviceId() },
    undefined,
    deviceHeaders(),
  )
  return keepAnyIssuedToken(result)
}

export function getApprovedMessages(zoneId: string): Promise<PublicMessage[]> {
  return apiGet<PublicMessage[]>(`/api/care/zones/${encodeURIComponent(zoneId)}/messages`)
}
