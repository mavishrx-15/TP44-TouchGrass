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
  speciesCount: number
}

export interface TreeZone {
  id: string
  precinctId: string
  label: string
  center: Coordinates
  treeCount: number
  density: DensityTier
  dominantGenus: TreeGenus
  distanceKm: number
  description: string
  mapPosition: { x: number; y: number; width: number; height: number }
}

export interface TreeRecord {
  id: string
  precinctId: string
  coordinates: Coordinates
  commonName: string
  scientificName: string
  genus: TreeGenus
  plantingAge: string
  distanceKm: number
  mapPosition: { x: number; y: number }
}

export interface NeighbourhoodSnapshot {
  treeCount: number
  zoneCount: number
  speciesCount: number
}

export interface RouteOption {
  id: 'fastest' | 'green'
  label: string
  durationMinutes: number
  distanceKm: number
  treeCount: number
}
