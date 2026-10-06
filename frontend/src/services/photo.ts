/**
 * Photo preparation for Epic 7. Every photo is drawn onto a canvas and encoded
 * again as a fresh JPEG. That drops the original file's metadata, including the
 * GPS location the camera embeds (US7.1 quality rule: hidden location data is
 * removed before saving). The result is also resized so it fits the server limit.
 */

const LIMITS: [maxSide: number, quality: number][] = [
  [1280, 0.85],
  [960, 0.7],
  [720, 0.6],
]
/** Stay under the server's 2,000,000-character photo limit with margin. */
const MAX_CHARS = 1_900_000

export async function encodePhoto(source: CanvasImageSource, width: number, height: number): Promise<string> {
  for (const [maxSide, quality] of LIMITS) {
    const scale = Math.min(1, maxSide / Math.max(width, height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(width * scale))
    canvas.height = Math.max(1, Math.round(height * scale))
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Photo could not be prepared on this device.')
    context.drawImage(source, 0, 0, canvas.width, canvas.height)
    const dataUrl = canvas.toDataURL('image/jpeg', quality)
    if (dataUrl.length <= MAX_CHARS) return dataUrl
  }
  throw new Error('That photo is too large. Try a closer shot.')
}

export async function photoFromFile(file: File): Promise<string> {
  const bitmap = await createImageBitmap(file)
  try {
    return await encodePhoto(bitmap, bitmap.width, bitmap.height)
  } finally {
    bitmap.close()
  }
}

export function photoFromVideo(video: HTMLVideoElement): Promise<string> {
  return encodePhoto(video, video.videoWidth, video.videoHeight)
}
