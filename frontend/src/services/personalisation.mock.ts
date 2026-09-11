import type { Area } from '@/types/personalisation'
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

export function mockAreas(precinct: Precinct): Area[] {
  const streets: Record<string, (string | null)[]> = {
    kensington: ['Macaulay Rd', 'Bellair St', null],
    parkville: ['Royal Parade', 'Gatehouse St', null],
    'melbourne-cbd': ['Spring St', 'Victoria St', null],
    'north-melbourne': ['Errol St', 'Arden St', null],
    docklands: ['Harbour Esplanade', 'Bourke St', null],
  }
  return [
    {
      trees: 156,
      canopy: 0.92,
      park: 0.86,
      allergy: 0.72,
      pollen: 2,
      lat: 0.004,
      lng: 0.004,
      genus: 'Eucalyptus' as const,
    },
    {
      trees: 88,
      canopy: 0.58,
      park: 0.25,
      allergy: 0.96,
      pollen: 0,
      lat: -0.002,
      lng: 0.002,
      genus: 'Corymbia' as const,
    },
    {
      trees: 203,
      canopy: 0.97,
      park: 0.6,
      allergy: null,
      pollen: null,
      lat: 0.01,
      lng: 0.006,
      genus: 'Eucalyptus' as const,
    },
  ].map((item, index) => {
    const center = {
      lat: precinct.referencePoint.lat + item.lat,
      lng: precinct.referencePoint.lng + item.lng,
    }
    const nearestStreet = streets[precinct.id]?.[index] ?? null
    return {
      id: `${precinct.id}-${index}`,
      precinctId: precinct.id,
      precinctName: precinct.name,
      label: nearestStreet ? `${precinct.name} · ${nearestStreet} Area` : precinct.name,
      nearestStreet,
      center,
      bounds: {
        north: center.lat + 0.0005,
        south: center.lat - 0.0005,
        east: center.lng + 0.0005,
        west: center.lng - 0.0005,
      },
      treeCount: item.trees,
      density: index === 1 ? 'Medium' : 'High',
      dominantGenus: item.genus,
      distanceKm: 0,
      description: 'Illustrative tree-density area.',
      mapPosition: { x: 0, y: 0, width: 0, height: 0 },
      metrics: {
        canopy: item.canopy,
        parkShare: item.park,
        lowAllergyShare: item.allergy,
        highPollenTrees: item.pollen,
      },
      genera: [
        { name: item.genus, count: Math.round(item.trees * 0.4) },
        { name: index === 2 ? 'Ulmus' : 'Platanus', count: Math.round(item.trees * 0.18) },
        { name: 'Casuarina', count: Math.round(item.trees * 0.09) },
      ],
      dataNotes: [
        'Illustrative tree and canopy data; allergy classification is awaiting confirmation.',
        ...(!nearestStreet ? ['Nearby street is not available for this area.'] : []),
      ],
    }
  })
}
