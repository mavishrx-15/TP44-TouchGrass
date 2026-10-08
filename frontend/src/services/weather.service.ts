import { apiGet } from '@/api/client'

export type WeatherBand = 'warm' | 'mild' | 'cool'

export interface CbdWeather {
  temperatureC: number
  band: WeatherBand
  observedAt: string
  source: string
}

/**
 * Current CBD temperature for Sprout's Step 3 (US5.3). Null on any error or
 * if the backend takes longer than 3 seconds - callers fall back to a
 * neutral question rather than waiting on, or guessing, a temperature.
 */
export function getCbdWeather(): Promise<CbdWeather | null> {
  return apiGet<CbdWeather>('/api/weather/now', AbortSignal.timeout(3000)).catch(() => null)
}
