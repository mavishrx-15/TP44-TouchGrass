// @vitest-environment jsdom
import { beforeEach, expect, it, vi } from 'vitest'
import type { PredictionType } from 'nsfwjs'

const { classify } = vi.hoisted(() => ({ classify: vi.fn() }))
vi.mock('nsfwjs/core', () => ({ load: vi.fn(async () => ({ classify })) }))
vi.mock('nsfwjs/models/mobilenet_v2', () => ({ MobileNetV2Model: {} }))
import { isUnsafePhoto, requireSafePhoto } from '@/services/moderation'

function scores(porn = 0, sexy = 0, hentai = 0): PredictionType[] {
  return [
    { className: 'Porn', probability: porn },
    { className: 'Sexy', probability: sexy },
    { className: 'Hentai', probability: hentai },
    { className: 'Neutral', probability: 1 - porn - sexy - hentai },
    { className: 'Drawing', probability: 0 },
  ]
}

beforeEach(() => {
  classify.mockReset()
  vi.stubGlobal(
    'Image',
    class {
      src = ''
      decode = async () => {}
    },
  )
})

it('uses combined adult-content probability', () => {
  expect(isUnsafePhoto(scores(0.2, 0.2, 0.1))).toBe(true)
  expect(isUnsafePhoto(scores(0.01, 0.01, 0.01))).toBe(false)
})

it('allows safe photos and blocks unsafe photos', async () => {
  classify.mockResolvedValueOnce(scores()).mockResolvedValueOnce(scores(0.9))
  await expect(requireSafePhoto('data:image/jpeg;base64,test')).resolves.toBeUndefined()
  await expect(requireSafePhoto('data:image/jpeg;base64,test')).rejects.toThrow('adult content')
})

it('blocks upload on classifier failure or invalid predictions', async () => {
  classify.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce([])
  await expect(requireSafePhoto('test')).rejects.toThrow('could not check')
  await expect(requireSafePhoto('test')).rejects.toThrow('could not check')
})
