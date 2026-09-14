export type DensityTier = 'High' | 'Medium' | 'Low'

export type TreeGenus =
  | 'Eucalyptus'
  | 'Acacia'
  | 'Ulmus'
  | 'Platanus'
  | 'Corymbia'
  | 'Allocasuarina'
  | 'Casuarina'
  | 'Quercus'
  | 'Other'

export interface Coordinates {
  lat: number
  lng: number
}

export interface Precinct {
  id: string
  name: string
  referencePoint: Coordinates
  treeCount: number
  zoneCount: number
  speciesCount: number
}

export interface MapBounds {
  north: number
  south: number
  east: number
  west: number
}

export interface TreeZone {
  id: string
  precinctId: string
  label: string
  nearestStreet: string | null
  center: Coordinates
  bounds: MapBounds
  treeCount: number
  density: DensityTier
  dominantGenus: TreeGenus | null
  distanceKm: number
  description: string
  mapPosition: { x: number; y: number; width: number; height: number }
}

export interface TreeRecord {
  id: string
  precinctId: string
  zoneId: string
  coordinates: Coordinates
  commonName: string
  scientificName: string
  family: string
  genus: TreeGenus
  plantingAge: string
  lifeExpectancy: string
  locatedIn: 'Park' | 'Street'
  distanceKm: number
  mapPosition: { x: number; y: number }
}

export interface NeighbourhoodSnapshot {
  treeCount: number
  zoneCount: number
  speciesCount: number
}

export interface RouteOption {
  id: 'personalised'
  label: string
  durationMinutes: number
  distanceKm: number
  treeCount: number
  encodedPolyline?: string
}

export interface PlaceSuggestion {
  id: string
  label: string
}

export interface RoutePlace extends PlaceSuggestion {
  coordinates: Coordinates
}

export type RouteEndpoint = TreeZone | RoutePlace | null
