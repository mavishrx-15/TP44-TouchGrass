<script setup lang="ts">
import { importLibrary, setOptions } from '@googlemaps/js-api-loader'
import { onBeforeUnmount, onMounted, shallowRef, watch } from 'vue'
import type { Coordinates, RouteOption, TreeRecord, TreeZone } from '@/types/discovery'

const props = defineProps<{
  center: Coordinates
  trees: TreeRecord[]
  zones: TreeZone[]
  directionsOpen: boolean
  selectedRouteId: RouteOption['id']
}>()

const emit = defineEmits<{
  selectTree: [tree: TreeRecord]
  selectZone: [zone: TreeZone]
  error: [message: string]
}>()

const mapElement = shallowRef<HTMLElement | null>(null)
const map = shallowRef<google.maps.Map | null>(null)
let markers: google.maps.marker.AdvancedMarkerElement[] = []
let rectangles: google.maps.Rectangle[] = []
let routeLines: google.maps.Polyline[] = []

const genusColours: Record<TreeRecord['genus'], string> = {
  Eucalyptus: '#31854a',
  Acacia: '#d6a52b',
  Ulmus: '#7655b6',
  Platanus: '#337dcc',
  Corymbia: '#31854a',
  Allocasuarina: '#9b8b67',
  Casuarina: '#9b8b67',
  Quercus: '#bd62ad',
  Other: '#8c8065',
}

function clearMarkers() {
  markers.forEach((marker) => (marker.map = null))
  markers = []
}

function clearRectangles() {
  rectangles.forEach((rectangle) => rectangle.setMap(null))
  rectangles = []
}

function clearRoutes() {
  routeLines.forEach((line) => line.setMap(null))
  routeLines = []
}

async function renderMarkers() {
  if (!map.value) return
  clearMarkers()

  const { AdvancedMarkerElement } = (await importLibrary('marker')) as google.maps.MarkerLibrary

  markers = props.trees.map((tree) => {
    const markerContent = document.createElement('span')
    markerContent.className = 'google-tree-marker'
    markerContent.style.backgroundColor = genusColours[tree.genus]

    const marker = new AdvancedMarkerElement({
      map: map.value,
      position: tree.coordinates,
      title: `${tree.commonName} (${tree.scientificName})`,
      content: markerContent,
      gmpClickable: true,
    })
    marker.addListener('click', () => emit('selectTree', tree))
    return marker
  })
}

function renderZones() {
  if (!map.value) return
  clearRectangles()

  rectangles = props.zones.map((zone) => {
    const latitudeRadius = 0.00045
    const longitudeRadius = 0.00057
    const highDensity = zone.density === 'High'
    const rectangle = new google.maps.Rectangle({
      map: map.value,
      bounds: {
        north: zone.center.lat + latitudeRadius,
        south: zone.center.lat - latitudeRadius,
        east: zone.center.lng + longitudeRadius,
        west: zone.center.lng - longitudeRadius,
      },
      clickable: true,
      fillColor: highDensity ? '#1f662f' : '#69ad45',
      fillOpacity: highDensity ? 0.28 : 0.18,
      strokeColor: highDensity ? '#164e29' : '#559746',
      strokeOpacity: 0.65,
      strokeWeight: 2,
    })
    rectangle.addListener('click', () => emit('selectZone', zone))
    return rectangle
  })
}

function routePath(kind: RouteOption['id']): google.maps.LatLngLiteral[] {
  const { lat, lng } = props.center
  if (kind === 'fastest') {
    return [
      { lat: lat - 0.006, lng: lng - 0.005 },
      { lat: lat - 0.002, lng: lng - 0.001 },
      { lat: lat + 0.001, lng: lng + 0.003 },
      { lat: lat + 0.005, lng: lng + 0.006 },
    ]
  }
  return [
    { lat: lat - 0.006, lng: lng - 0.005 },
    { lat: lat - 0.004, lng: lng + 0.001 },
    { lat: lat + 0.002, lng: lng + 0.001 },
    { lat: lat + 0.005, lng: lng + 0.006 },
  ]
}

function renderRoutes() {
  if (!map.value) return
  clearRoutes()
  if (!props.directionsOpen) return

  routeLines = (['fastest', 'green'] as const).map(
    (id) =>
      new google.maps.Polyline({
        map: map.value!,
        path: routePath(id),
        clickable: false,
        strokeColor: id === 'green' ? '#247438' : '#347dcc',
        strokeOpacity: props.selectedRouteId === id ? 0.95 : 0.42,
        strokeWeight: props.selectedRouteId === id ? 7 : 5,
        zIndex: props.selectedRouteId === id ? 5 : 4,
      }),
  )
}

function resetView() {
  map.value?.setCenter(props.center)
  map.value?.setZoom(15)
}

defineExpose({ resetView })

onMounted(async () => {
  const key = import.meta.env.VITE_GOOGLE_MAPS_API_KEY?.trim()
  if (!key) {
    emit('error', 'Google Maps API key is missing from frontend/.env.local.')
    return
  }

  try {
    setOptions({ key, v: 'weekly', language: 'en', region: 'AU' })
    const { Map } = (await importLibrary('maps')) as google.maps.MapsLibrary
    if (!mapElement.value) return

    map.value = new Map(mapElement.value, {
      center: props.center,
      zoom: 15,
      mapId: import.meta.env.VITE_GOOGLE_MAP_ID || 'DEMO_MAP_ID',
      mapTypeControl: false,
      fullscreenControl: false,
      streetViewControl: false,
      clickableIcons: false,
      gestureHandling: 'greedy',
    })

    await renderMarkers()
    renderZones()
    renderRoutes()
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown Google Maps error'
    emit('error', `Google Maps could not load: ${message}`)
  }
})

watch(
  () => props.center,
  () => resetView(),
  { deep: true },
)
watch(() => props.trees, renderMarkers, { deep: true })
watch(() => props.zones, renderZones, { deep: true })
watch(() => [props.directionsOpen, props.selectedRouteId, props.center], renderRoutes, {
  deep: true,
})

onBeforeUnmount(() => {
  clearMarkers()
  clearRectangles()
  clearRoutes()
})
</script>

<template>
  <div ref="mapElement" class="google-map" />
</template>

<style>
.google-map {
  position: absolute;
  inset: 0;
}

.google-tree-marker {
  display: block;
  width: 18px;
  height: 18px;
  border: 3px solid white;
  border-radius: 50%;
  box-shadow: 0 2px 7px rgb(23 53 29 / 28%);
  cursor: pointer;
  transition: transform 150ms ease;
}

.google-tree-marker:hover {
  transform: scale(1.35);
}
</style>
