import type { Precinct, RoutePlace } from '@/types/discovery'

export const mockPrecincts: Precinct[] = [
  ['melbourne-cbd', 'Melbourne CBD', -37.8136, 144.9631],
  ['kensington', 'Kensington', -37.7934, 144.9305],
  ['parkville', 'Parkville', -37.7885, 144.9517],
  ['north-melbourne', 'North Melbourne', -37.8021, 144.944],
  ['docklands', 'Docklands', -37.815, 144.946],
].map(([id, name, lat, lng]) => ({
  id: String(id),
  name: String(name),
  referencePoint: { lat: Number(lat), lng: Number(lng) },
  treeCount: 0,
  zoneCount: 3,
  speciesCount: 0,
}))

export const mockPlaces: RoutePlace[] = [
  {
    id: 'demo-flinders',
    label: '123 Flinders Street, Melbourne',
    coordinates: { lat: -37.816, lng: 144.9705 },
  },
  {
    id: 'demo-kensington',
    label: 'Kensington Station, Kensington',
    coordinates: { lat: -37.7942, lng: 144.9308 },
  },
  {
    id: 'demo-geelong',
    label: 'Geelong Station, Geelong',
    coordinates: { lat: -38.1447, lng: 144.3556 },
  },
]
