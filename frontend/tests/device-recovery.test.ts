// @vitest-environment jsdom
import { beforeEach, expect, it, vi } from 'vitest'
vi.mock('@/services/moderation', () => ({ requireSafePhoto: vi.fn(async () => {}) }))

const input = {
  zoneId: null,
  latitude: -37.81,
  longitude: 144.96,
  accuracyM: 10,
  photoDataUrl: null,
}
const response = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

beforeEach(() => {
  vi.restoreAllMocks()
  vi.resetModules()
  localStorage.clear()
  sessionStorage.clear()
})

it('recovers a missing credential for a new pin and uses the replacement for its photo', async () => {
  localStorage.setItem('touchgrass.device.id', 'old-device')
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(response(403, { detail: 'Invalid device credential.' }))
    .mockResolvedValueOnce(response(201, { id: 'pin', deviceToken: 'new-token' }))
    .mockResolvedValueOnce(response(200, { id: 'pin' }))
  vi.stubGlobal('fetch', fetch)
  const { createPin, updatePinPhoto } = await import('@/services/care.service')
  await createPin(input)
  const first = JSON.parse(fetch.mock.calls[0]![1].body)
  const retried = JSON.parse(fetch.mock.calls[1]![1].body)
  expect(first.deviceId).toBe('old-device')
  expect(retried.deviceId).not.toBe('old-device')
  expect(localStorage.getItem('touchgrass.device.token')).toBe('new-token')
  await updatePinPhoto('pin', 'data:image/jpeg;base64,AQID')
  expect(JSON.parse(fetch.mock.calls[2]![1].body).deviceId).toBe(retried.deviceId)
  expect(fetch.mock.calls[2]![1].headers['X-Device-Token']).toBe('new-token')
})

it.each([429, 403])('does not rotate identity or retry other failures (%s)', async (status) => {
  localStorage.setItem('touchgrass.device.id', 'old-device')
  const fetch = vi.fn().mockResolvedValue(response(status, { detail: 'Request refused.' }))
  vi.stubGlobal('fetch', fetch)
  const { createPin } = await import('@/services/care.service')
  await expect(createPin(input)).rejects.toMatchObject({ status })
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(localStorage.getItem('touchgrass.device.id')).toBe('old-device')
})

it('retries an invalid credential only once', async () => {
  const fetch = vi
    .fn()
    .mockImplementation(async () => response(403, { detail: 'Invalid device credential.' }))
  vi.stubGlobal('fetch', fetch)
  const { createPin } = await import('@/services/care.service')
  await expect(createPin(input)).rejects.toMatchObject({ status: 403 })
  expect(fetch).toHaveBeenCalledTimes(2)
})

it('retains one session identity and token when browser storage is blocked', async () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('Blocked')
  })
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('Blocked')
  })
  const { getDeviceId, getDeviceToken, saveDeviceToken } = await import('@/services/device.service')
  const id = getDeviceId()
  saveDeviceToken('session-token')
  expect(getDeviceId()).toBe(id)
  expect(getDeviceToken()).toBe('session-token')
})
