const BASE_URL = import.meta.env.VITE_API_BASE_URL
const ACCESS_TOKEN_KEY = 'touchgrass_access_token'

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY)
}

export function setAccessToken(token: string): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, token)
}

export function clearAccessToken(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * Thin wrapper over fetch. Every backend call goes through here so that
 * base URL, headers and error shape are handled in one place.
 */
export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      Accept: 'application/json',
      ...(getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : {}),
    },
  })
  if (!response.ok) {
    throw new ApiError(`GET ${path} failed`, response.status)
  }
  return (await response.json()) as T
}
