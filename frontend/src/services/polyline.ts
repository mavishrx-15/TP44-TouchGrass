import type { Coordinates } from '@/types/discovery'

/**
 * Decodes a Google-encoded polyline into a dense list of points.
 *
 * The new `/api/sprout/route` response carries `encodedPolyline` instead of a
 * ready-made point array, so anything that needs the actual path (the live
 * walk's progress maths, the demo walk, off-route detection) decodes it here.
 * `GoogleMapCanvas` keeps its own copy for the green route line - duplicated
 * rather than imported, so the map component has no dependency beyond itself.
 */
export function decodePolyline(encoded: string): Coordinates[] {
  const points: Coordinates[] = []
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

function decodeValue(encoded: string, start: number): { value: number; index: number } {
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
