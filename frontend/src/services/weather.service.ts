import { apiGet } from '@/api/client'

export interface CbdWeather {
  temperatureCelsius: number | null
  available: boolean
}

export function getCbdWeather(signal?: AbortSignal): Promise<CbdWeather> {
  return apiGet<CbdWeather>('/api/weather/cbd', signal)
}
