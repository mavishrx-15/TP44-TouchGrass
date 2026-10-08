import { apiGet, apiPost, apiPut } from '@/api/client'

/** Epic 7 API client. Matches the contract at the top of backend/app/routers/care.py. */

export interface CarePin {
  id: string
  zoneId: string | null
  latitude: number
  longitude: number
  accuracyM: number
  hasPhoto: boolean
  photoStatus: 'pending' | 'approved' | 'rejected'
  createdAt: string
}

export interface CareMessage {
  id: string
  pinId: string
  zoneId: string | null
  body: string
  kind: 'message' | 'damage_report'
  status: 'pending' | 'approved' | 'rejected'
  createdAt: string
}

export interface PublicMessage {
  id: string
  body: string
  createdAt: string
  pin: { latitude: number; longitude: number }
  photoDataUrl: string | null
}

export function createPin(input: {
  zoneId: string | null
  latitude: number
  longitude: number
  accuracyM: number
  photoDataUrl: string | null
}): Promise<CarePin> {
  return apiPost<CarePin>('/api/care/pins', input)
}

export function updatePinPhoto(pinId: string, photoDataUrl: string): Promise<CarePin> {
  return apiPut<CarePin>(`/api/care/pins/${encodeURIComponent(pinId)}/photo`, { photoDataUrl })
}

export function postMessage(
  pinId: string,
  body: string,
  kind: CareMessage['kind'] = 'message',
): Promise<CareMessage> {
  return apiPost<CareMessage>(`/api/care/pins/${encodeURIComponent(pinId)}/messages`, { body, kind })
}

export function getApprovedMessages(zoneId: string): Promise<PublicMessage[]> {
  return apiGet<PublicMessage[]>(`/api/care/zones/${encodeURIComponent(zoneId)}/messages`)
}
