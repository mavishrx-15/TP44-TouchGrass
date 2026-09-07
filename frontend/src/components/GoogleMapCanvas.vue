<script setup lang="ts">
import { importLibrary, setOptions } from '@googlemaps/js-api-loader'
import { onBeforeUnmount, onMounted, shallowRef, watch } from 'vue'
import type { Coordinates, DensityTier, RouteOption, TreeRecord, TreeZone } from '@/types/discovery'

const props = defineProps<{
  center: Coordinates
  trees: TreeRecord[]
  zones: TreeZone[]
  directionsOpen: boolean
  selectedRouteId: RouteOption['id']
  routeOptions: RouteOption[]
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

// ColorBrewer's 3-class "Greens" sequential scale: built for map choropleths,
// so the three tiers stay distinct without turning neon or muddy on top of
// the basemap's own colours.
const densityStyles: Record<DensityTier, { fillColor: string; fillOpacity: number }> = {
  High: { fillColor: '#006d2c', fillOpacity: 0.55 },
  Medium: { fillColor: '#31a354', fillOpacity: 0.45 },
  Low: { fillColor: '#a1d99b', fillOpacity: 0.4 },
}

function clearMarkers() {
  // Google Maps overlays live outside Vue, so detach them before each redraw.
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
    const style = densityStyles[zone.density]
    const rectangle = new google.maps.Rectangle({
      map: map.value,
      bounds: zone.bounds,
      clickable: true,
      fillColor: style.fillColor,
      fillOpacity: style.fillOpacity,
      strokeWeight: 0,
    })
    rectangle.addListener('click', () => emit('selectZone', zone))
    return rectangle
  })
}

function renderRoutes() {
  if (!map.value) return
  clearRoutes()
  if (!props.directionsOpen) return

  // Draw every candidate route, then highlight the selected one through styling.
  const routeBounds = new google.maps.LatLngBounds()
  routeLines = props.routeOptions
    .filter((route) => route.encodedPolyline)
    .map((route) => {
      const path = decodePolyline(route.encodedPolyline!)
      path.forEach((point) => routeBounds.extend(point))
      return new google.maps.Polyline({
        map: map.value!,
        path,
        clickable: false,
        strokeColor: route.id === 'green' ? '#247438' : '#347dcc',
        strokeOpacity: props.selectedRouteId === route.id ? 0.95 : 0.42,
        strokeWeight: props.selectedRouteId === route.id ? 7 : 5,
        zIndex: props.selectedRouteId === route.id ? 5 : 4,
      })
    })
  if (!routeBounds.isEmpty()) map.value.fitBounds(routeBounds, 90)
}

function decodePolyline(encoded: string): google.maps.LatLngLiteral[] {
  // Google polylines store signed coordinate deltas rather than full coordinates.
  const points: google.maps.LatLngLiteral[] = []
  let index = 0
  let latitude = 0
  let longitude = 0
  while (index < encoded.length) {
    const latitudeValue = decodeValue(encoded, index)
    index = latitudeValue.index
    const longitudeValue = decodeValue(encoded, index)
    index = longitudeValue.index
    latitude += latitudeValue.value
    longitude += longitudeValue.value
    points.push({ lat: latitude / 100_000, lng: longitude / 100_000 })
  }
  return points
}

function decodeValue(encoded: string, start: number) {
  let result = 0
  let shift = 0
  let index = start
  let byte: number
  do {
    byte = encoded.charCodeAt(index++) - 63
    result |= (byte & 0x1f) << shift
    shift += 5
  } while (byte >= 0x20)
  return { value: result & 1 ? ~(result >> 1) : result >> 1, index }
}

function resetView() {
  map.value?.setCenter(props.center)
  map.value?.setZoom(15)
}

function focusZone(zone: TreeZone) {
  map.value?.fitBounds(zone.bounds, 90)
}

defineExpose({ resetView, focusZone })

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
      mapTypeControl: true,
      mapTypeControlOptions: {
        position: google.maps.ControlPosition.TOP_RIGHT,
        style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
      },
      fullscreenControl: true,
      fullscreenControlOptions: { position: google.maps.ControlPosition.TOP_RIGHT },
      scaleControl: true,
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
watch(() => [props.directionsOpen, props.selectedRouteId, props.routeOptions], renderRoutes, {
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
