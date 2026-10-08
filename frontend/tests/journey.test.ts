// @vitest-environment jsdom
// This file exercises the real api/client.ts (sessionStorage, window events),
// unlike the rest of the suite which runs under the lighter 'node' environment
// and stubs sessionStorage by hand where it's needed.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { apiGet, apiPost, clearAccessToken, getAccessToken, setAccessToken } from '@/api/client'

const token = (seconds: number) =>
  `${btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds })).replace(/=/g, '')}.signature`

beforeEach(() => {
  setActivePinia(createPinia())
  sessionStorage.clear()
  vi.stubGlobal('scrollTo', vi.fn())
})
afterEach(() => {
  clearAccessToken()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('access lifecycle', () => {
  it('uses session storage and rejects malformed and expired tokens', () => {
    setAccessToken(token(100))
    expect(getAccessToken()).not.toBeNull()
    sessionStorage.setItem('touchgrass_access_token', token(-1))
    expect(getAccessToken()).toBeNull()
    sessionStorage.setItem('touchgrass_access_token', 'nonsense')
    expect(getAccessToken()).toBeNull()
  })
  it('expires even without an API call or route change', () => {
    vi.useFakeTimers()
    const expired = vi.fn()
    window.addEventListener('access-expired', expired, { once: true })
    setAccessToken(token(2))
    vi.advanceTimersByTime(2100)
    expect(getAccessToken()).toBeNull()
    expect(expired).toHaveBeenCalledOnce()
  })
  it('sends bearer tokens on GET and POST and clears on 401', async () => {
    setAccessToken(token(100))
    const fetchMock = vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(
          new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } }),
        ),
      )
    vi.stubGlobal('fetch', fetchMock)
    await apiGet('/api/precincts')
    await apiPost('/api/routes', {})
    expect(
      fetchMock.mock.calls.every((call) => call[1].headers.Authorization.startsWith('Bearer ')),
    ).toBe(true)
    fetchMock.mockResolvedValue(new Response('{}', { status: 401 }))
    await expect(apiGet('/api/precincts')).rejects.toMatchObject({ status: 401 })
    expect(getAccessToken()).toBeNull()
  })
})

describe('route guard', () => {
  it('protects direct links, permits valid sessions and redirects expired sessions', async () => {
    const { default: router } = await import('@/router')
    await router.push('/rewards')
    expect(router.currentRoute.value.name).toBe('access')
    expect(router.currentRoute.value.query.redirect).toBe('/rewards')
    setAccessToken(token(100))
    await router.push('/')
    expect(router.currentRoute.value.name).toBe('home')
    sessionStorage.setItem('touchgrass_access_token', token(-1))
    await router.push('/walk')
    expect(router.currentRoute.value.name).toBe('access')
  })
})
