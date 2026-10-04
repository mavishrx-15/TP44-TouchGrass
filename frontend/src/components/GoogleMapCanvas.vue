<script setup lang="ts">
import { importLibrary, setOptions } from '@googlemaps/js-api-loader'
import { computed, onBeforeUnmount, onMounted, shallowRef, watch } from 'vue'
import type {
  Coordinates,
  DensityTier,
  MapBounds,
  RouteOption,
  TreeRecord,
  TreeZone,
} from '@/types/discovery'

const props = defineProps<{
  center: Coordinates
  trees: TreeRecord[]
  zones: TreeZone[]
  directionsOpen: boolean
  routeOptions: RouteOption[]
  origin?: Coordinates
  destination?: Coordinates
  previewPath?: Coordinates[]
  demo?: boolean
  compact?: boolean
  // Recentring and resetting zoom every time `center` moves fights any
  // manual pan/zoom once the map is showing a whole area, not just one
  // destination pin. Defaults to the existing behaviour for callers that
  // rely on it (MapView's search bar, the recommendation card thumbnail).
  autoCenter?: boolean
  // Epic 5, US5.5: "a dashed line marks the CBD edge" on Sprout's map step.
  cbdBounds?: MapBounds
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
let endpointMarkers: google.maps.marker.AdvancedMarkerElement[] = []
let cbdOutline: google.maps.Polyline | null = null
let disposed = false

const previewPoints = computed(() => {
  if (props.compact) return [{ x: 300, y: 125 }]
  const points = props.previewPath?.length
    ? props.previewPath
    : [
        props.origin ?? { lat: props.center.lat - 0.006, lng: props.center.lng - 0.008 },
        props.destination ?? props.center,
      ]
  const lats = points.map((p) => p.lat),
    lngs = points.map((p) => p.lng)
  const minLat = Math.min(...lats),
    maxLat = Math.max(...lats),
    minLng = Math.min(...lngs),
    maxLng = Math.max(...lngs)
  const range = Math.max(maxLat - minLat, (maxLng - minLng) * 0.79, 0.003)
  return points.map((p) => ({
    x: 300 + (((p.lng - (minLng + maxLng) / 2) * 0.79) / range) * 370,
    y: 405 - ((p.lat - (minLat + maxLat) / 2) / range) * 260,
  }))
})
const previewLine = computed(() => previewPoints.value.map((p) => `${p.x},${p.y}`).join(' '))
const previewStart = computed(() => previewPoints.value[0]!)
const previewEnd = computed(() => previewPoints.value[previewPoints.value.length - 1]!)

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
  if (disposed) return

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

function renderCbdOutline() {
  cbdOutline?.setMap(null)
  cbdOutline = null
  if (!map.value || !props.cbdBounds) return
  const { north, south, east, west } = props.cbdBounds
  const path = [
    { lat: north, lng: west },
    { lat: north, lng: east },
    { lat: south, lng: east },
    { lat: south, lng: west },
    { lat: north, lng: west },
  ]
  // Rectangle has no dashed stroke option - a dashed line is a Polyline
  // whose visible stroke is a repeating short-dash icon instead.
  cbdOutline = new google.maps.Polyline({
    map: map.value,
    path,
    clickable: false,
    strokeOpacity: 0,
    zIndex: 2,
    icons: [
      {
        icon: { path: 'M 0,-1 0,1', strokeOpacity: 1, strokeColor: '#1f5a2c', scale: 3 },
        offset: '0',
        repeat: '14px',
      },
    ],
  })
}

function renderRoutes() {
  if (!map.value) return
  clearRoutes()
  if (!props.directionsOpen) return

  // The personalised flow renders exactly one route.
  const routeBounds = new google.maps.LatLngBounds()
  routeLines = props.routeOptions
    .slice(0, 1)
    .filter((route) => route.encodedPolyline)
    .map((route) => {
      const path = decodePolyline(route.encodedPolyline!)
      path.forEach((point) => routeBounds.extend(point))
      return new google.maps.Polyline({
        map: map.value!,
        path,
        clickable: false,
        strokeColor: '#247438',
        strokeOpacity: 0.95,
        strokeWeight: 6,
        zIndex: 5,
      })
    })
  if (!routeBounds.isEmpty())
    map.value.fitBounds(routeBounds, { top: 230, bottom: 40, left: 35, right: 35 })
}

async function renderEndpoints() {
  endpointMarkers.forEach((marker) => {
    marker.map = null
  })
  endpointMarkers = []
  if (!map.value) return
  const { AdvancedMarkerElement } = (await importLibrary('marker')) as google.maps.MarkerLibrary
  if (disposed) return
  const bounds = new google.maps.LatLngBounds()
  for (const [title, position] of [
    ['Starting location', props.origin],
    ['Destination', props.destination],
  ] as const) {
    if (!position) continue
    bounds.extend(position)
    const content = document.createElement('span')
    content.className =
      title === 'Starting location' ? 'journey-origin-marker' : 'journey-destination-marker'
    // AdvancedMarkerElement's own `title` sets the accessible name but,
    // unlike the legacy Marker, doesn't show a hover tooltip - the DOM
    // element's native `title` attribute is what actually renders one.
    content.title = title
    endpointMarkers.push(new AdvancedMarkerElement({ map: map.value, position, title, content }))
  }
  if (!props.routeOptions.length && !bounds.isEmpty()) {
    // fitBounds on a single point (the common case here: just a destination,
    // no origin) zooms in as far as possible - a card thumbnail ends up
    // showing nothing but a solid green blob. Cap it back to a level that
    // still reads as "a neighbourhood", same as a real two-point fit would.
    const maxZoom = props.compact ? 15 : 16
    google.maps.event.addListenerOnce(map.value, 'bounds_changed', () => {
      if ((map.value?.getZoom() ?? 0) > maxZoom) map.value?.setZoom(maxZoom)
    })
    map.value.fitBounds(bounds, props.compact ? 30 : 90)
  }
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
  if (props.demo) return
  const key = import.meta.env.VITE_GOOGLE_MAPS_API_KEY?.trim()
  if (!key) {
    emit(
      'error',
      'The map is unavailable right now. You can still review your route details below.',
    )
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
      ...(props.compact
        ? { disableDefaultUI: true, gestureHandling: 'none', keyboardShortcuts: false }
        : {}),
    })

    await renderMarkers()
    renderZones()
    renderCbdOutline()
    renderRoutes()
    await renderEndpoints()
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown Google Maps error'
    emit('error', `Google Maps could not load: ${message}`)
  }
})

watch(
  () => props.center,
  () => {
    if (props.autoCenter !== false) resetView()
  },
  { deep: true },
)
watch(() => props.trees, renderMarkers, { deep: true })
watch(() => props.zones, renderZones, { deep: true })
watch(() => props.cbdBounds, renderCbdOutline, { deep: true })
watch(() => [props.directionsOpen, props.routeOptions], renderRoutes, {
  deep: true,
})
watch(() => [props.origin, props.destination], renderEndpoints, { deep: true })

onBeforeUnmount(() => {
  disposed = true
  clearMarkers()
  clearRectangles()
  clearRoutes()
  cbdOutline?.setMap(null)
  endpointMarkers.forEach((marker) => {
    marker.map = null
  })
})
</script>

<template>
  <div
    v-if="demo"
    class="google-map demo-map"
    role="img"
    :aria-label="`Illustrative location map near ${center.lat.toFixed(3)}, ${center.lng.toFixed(3)}${directionsOpen ? ', with a sample route' : ''}`"
  >
    <svg
      :viewBox="compact ? '0 0 600 260' : '0 0 600 600'"
      :preserveAspectRatio="compact ? 'xMidYMid slice' : 'xMidYMid meet'"
      aria-hidden="true"
    >
      <rect width="600" height="600" fill="#eef1e7" />
      <g stroke="#d9e0cc" stroke-width="1.5">
        <path
          d="M0 95H600M0 205H600M0 315H600M0 435H600M0 545H600M75 0V600M185 0V600M315 0V600M455 0V600M560 0V600"
        />
      </g>
      <g fill="#d6e7c2">
        <ellipse cx="78" cy="142" rx="49" ry="34" />
        <ellipse cx="420" cy="111" rx="52" ry="42" />
        <ellipse cx="492" cy="432" rx="59" ry="45" />
        <ellipse cx="160" cy="411" rx="50" ry="35" />
        <ellipse cx="295" cy="514" rx="43" ry="34" />
      </g>
      <g fill="#78aa6b" opacity=".8">
        <circle cx="55" cy="126" r="2.5" />
        <circle cx="101" cy="159" r="2.5" />
        <circle cx="469" cy="452" r="2.5" />
        <circle cx="497" cy="410" r="2.5" />
      </g>
      <ellipse
        :cx="previewEnd.x"
        :cy="previewEnd.y"
        rx="62"
        ry="47"
        fill="#b9d6a2"
        fill-opacity=".72"
        stroke="#398241"
        stroke-width="1.5"
        stroke-dasharray="4 4"
      />
      <template v-if="directionsOpen && previewPath?.length">
        <polyline
          :points="previewLine"
          fill="none"
          stroke="#1f662f"
          stroke-width="4"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <polyline
          :points="previewLine"
          fill="none"
          stroke="#a7c98b"
          stroke-width="1.5"
          stroke-dasharray="1 8"
        />
        <circle
          :cx="previewStart.x"
          :cy="previewStart.y"
          r="6"
          fill="white"
          stroke="#347dcc"
          stroke-width="3"
        />
      </template>
      <g :transform="`translate(${previewEnd.x - 12},${previewEnd.y - 25})`">
        <path d="M12 0C5 0 0 5 0 12c0 9 12 20 12 20s12-11 12-20C24 5 19 0 12 0Z" fill="#226934" />
        <circle cx="12" cy="11" r="4" fill="white" />
      </g>
    </svg>
    <span class="demo-map-label">Illustrative map{{ compact ? '' : ' · not for navigation' }}</span>
  </div>
  <div v-else ref="mapElement" class="google-map" />
</template>

<style>
.google-map {
  position: absolute;
  inset: 0;
}
.demo-map {
  overflow: hidden;
}
.demo-map > svg {
  display: block;
  width: 100%;
  height: 100%;
}
.demo-map-label {
  position: absolute;
  bottom: 8px;
  right: 8px;
  border-radius: 4px;
  background: #ffffffdf;
  color: #64725f;
  font: 10px/1.3 system-ui;
  padding: 3px 6px;
}
.journey-origin-marker,
.journey-destination-marker {
  display: block;
  width: 19px;
  height: 19px;
  border-radius: 50%;
  border: 4px solid #347dcc;
  background: white;
  box-shadow: 0 2px 5px #0003;
}
.journey-destination-marker {
  width: 26px;
  height: 26px;
  border: 6px solid #226934;
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
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
