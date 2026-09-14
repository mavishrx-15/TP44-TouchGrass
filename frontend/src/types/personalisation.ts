import type {
  Coordinates,
  Precinct,
  RouteOption,
  RoutePlace,
  TreeZone,
  TreeRecord,
} from './discovery'

export interface Preferences {
  canopy: number | null
  shade: number | null
  noise: 'quiet' | 'lively' | null
  allergy: 'avoid' | 'lower' | null
  walkingTime: 5 | 10 | 15 | 20 | null
}

export const emptyPreferences = (): Preferences => ({
  canopy: null,
  shade: null,
  noise: null,
  allergy: null,
  walkingTime: null,
})

export type TravelMode = 'WALK' | 'TRANSIT'
export interface AreaMetrics {
  canopy: number | null
  parkShare: number | null
  lowAllergyShare: number | null
  highPollenTrees: number | null
}
export interface Area extends TreeZone {
  precinctName: string
  metrics: AreaMetrics
  genera: { name: string; count: number }[]
  dataNotes: string[]
  trees?: TreeRecord[]
}
export interface PreferenceMatch {
  key: 'canopy' | 'shade' | 'noise' | 'allergy' | 'time'
  label: string
  detail: string
  matched: boolean
  value: number
}
export interface MatchSummary {
  score: number
  matches: PreferenceMatch[]
  sentence: string
}
export interface Recommendation extends Area {
  estimatedMinutes: number
  match: MatchSummary
}
export interface PersonalisedRoute extends RouteOption {
  travelMode: TravelMode
  match: MatchSummary | null
  metrics: AreaMetrics | null
  candidateCount: number
  message: string | null
  isMock: boolean
  path?: Coordinates[]
}
export interface PersonalisedRequest {
  origin: Coordinates
  destination: Coordinates
  preferences: Preferences
  travelMode: TravelMode
  precinctId: string
}
export interface JourneyContext {
  preferences: Preferences
  startLocation: RoutePlace | null
  destination: RoutePlace | null
}
export interface Coverage {
  precinct: Precinct
  distanceKm: number
  outside: boolean
}
