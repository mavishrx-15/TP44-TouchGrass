/** NSFWJS is also used by nsfw-filter. Classification stays on this device.
 * This is an extra browser filter; server-side approval remains mandatory.
 */
import type { NSFWJS, PredictionType } from 'nsfwjs'

let modelPromise: Promise<NSFWJS> | undefined

async function getModel(): Promise<NSFWJS> {
  if (!modelPromise) {
    modelPromise = Promise.all([import('nsfwjs/core'), import('nsfwjs/models/mobilenet_v2')])
      .then(([nsfwjs, { MobileNetV2Model }]) =>
        nsfwjs.load('MobileNetV2', { modelDefinitions: [MobileNetV2Model] }),
      )
      .catch((error) => {
        modelPromise = undefined
        throw error
      })
  }
  return modelPromise
}

export function isUnsafePhoto(predictions: PredictionType[]): boolean {
  const unsafe = predictions.filter((p) => ['Porn', 'Hentai', 'Sexy'].includes(p.className))
  return (
    unsafe.some((p) => !Number.isFinite(p.probability)) ||
    unsafe.reduce((sum, p) => sum + p.probability, 0) >= 0.5
  )
}

export async function requireSafePhoto(dataUrl: string): Promise<void> {
  let predictions: PredictionType[]
  try {
    const image = new Image()
    image.src = dataUrl
    await image.decode()
    const model = await getModel()
    predictions = await model.classify(image)
    if (predictions.length !== 5 || predictions.some((p) => !Number.isFinite(p.probability))) {
      throw new Error('Invalid classification')
    }
  } catch {
    throw new Error('We could not check this photo. Please try again or continue without a photo.')
  }
  if (isUnsafePhoto(predictions)) {
    throw new Error('This photo may contain adult content. Please choose a photo of your tree.')
  }
}
