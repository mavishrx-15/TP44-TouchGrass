const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

const ACCESS_TOKEN_KEY = 'touchgrass_access_token'
let expiryTimer: ReturnType<typeof setTimeout> | undefined

export function clearAccessToken(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  clearTimeout(expiryTimer)
}

export function getAccessToken(): string | null {
  const token = sessionStorage.getItem(ACCESS_TOKEN_KEY)
  if (!token) return null
  try {
    const [payload, signature, extra] = token.split('.')
    if (!payload || !signature || extra) throw new Error('Invalid token')
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const { exp } = JSON.parse(atob(normalized)) as { exp: number }
    if (!Number.isFinite(exp) || exp * 1000 <= Date.now()) throw new Error('Expired token')
    return token
  } catch {
    clearAccessToken()
    return null
  }
}

export function watchAccessExpiry(): void {
  clearTimeout(expiryTimer)
  const token = getAccessToken()
  if (!token) return
  const payload = token.split('.')[0]!.replace(/-/g, '+').replace(/_/g, '/')
  const { exp } = JSON.parse(atob(payload)) as { exp: number }
  expiryTimer = setTimeout(
    () => {
      clearAccessToken()
      window.dispatchEvent(new Event('access-expired'))
    },
    Math.min(exp * 1000 - Date.now(), 2147483647),
  )
}

export function setAccessToken(token: string): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, token)
  if (!getAccessToken()) throw new Error('Invalid access token')
  watchAccessExpiry()
}

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'

interface RequestOptions {
  method?: HttpMethod
  body?: unknown
  signal?: AbortSignal
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * Thin wrapper over fetch. Every backend call goes through here so that
 * base URL, headers and error shape are handled in one place.
 */
async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: HeadersInit = { Accept: 'application/json' }
  const token = getAccessToken()
  if (token && path !== '/api/access/verify') headers.Authorization = `Bearer ${token}`

  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  })

  if (!response.ok) {
    if (response.status === 401 && path !== '/api/access/verify') {
      clearAccessToken()
      window.dispatchEvent(new Event('access-expired'))
    }
    const contentType = response.headers.get('content-type')
    const detail = contentType?.includes('application/json')
      ? await response.json().catch(() => undefined)
      : await response.text().catch(() => undefined)
    throw new ApiError(`${method} ${path} failed`, response.status, detail)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { signal })
}

export function apiPost<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { method: 'POST', body, signal })
}

export function apiPut<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { method: 'PUT', body, signal })
}

export function apiDelete<T = void>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { method: 'DELETE', signal })
}
