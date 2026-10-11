// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PinTreeFlow from '@/components/walk/PinTreeFlow.vue'
import { createPin, postMessage } from '@/services/care.service'
import { ApiError } from '@/api/client'
import { apiGet } from '@/api/client'
vi.mock('@/api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/client')>()),
  apiGet: vi.fn(),
}))

vi.mock('@/services/care.service', () => ({
  createPin: vi.fn(),
  postMessage: vi.fn(),
  updatePinPhoto: vi.fn(),
}))

const fix = {
  coords: { latitude: -37.81, longitude: 144.95, accuracy: 150 },
  timestamp: Date.now(),
} as GeolocationPosition

beforeEach(() => {
  vi.clearAllMocks()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('pinning with a weak GPS fix', () => {
  it('saves the fix that was confirmed without asking for GPS a second time', async () => {
    const locate = vi.fn((success: PositionCallback) => success(fix))
    vi.stubGlobal('navigator', { geolocation: { getCurrentPosition: locate } })
    vi.mocked(createPin).mockResolvedValue({
      id: 'pin-1',
      zoneId: 'zone-1',
      latitude: -37.81,
      longitude: 144.95,
      accuracyM: 150,
      hasPhoto: false,
      photoStatus: 'pending',
      createdAt: '2026-10-09',
    })
    const wrapper = mount(PinTreeFlow, {
      props: { zoneId: 'zone-1', landmark: 'Flagstaff Gardens' },
      global: { stubs: { ElIcon: true, CameraCapture: true } },
    })
    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('Drop a pin here'))!
      .trigger('click')
    await flushPromises()
    expect(createPin).not.toHaveBeenCalled()
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Pin it anyway')!
      .trigger('click')
    await flushPromises()
    expect(locate).toHaveBeenCalledOnce()
    expect(createPin).toHaveBeenCalledWith({
      zoneId: 'zone-1',
      latitude: -37.81,
      longitude: 144.95,
      accuracyM: 150,
      photoDataUrl: null,
    })
    expect(wrapper.text()).toContain('YOUR TREE PIN')
    wrapper.unmount()
  })

  it('shows a readable save error instead of a raw API path', async () => {
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: (success: PositionCallback) =>
          success({ ...fix, coords: { ...fix.coords, accuracy: 5 } } as GeolocationPosition),
      },
    })
    vi.mocked(createPin).mockRejectedValue(new ApiError('POST /api/care/pins failed', 500))
    const wrapper = mount(PinTreeFlow, {
      props: { zoneId: 'zone-1', landmark: 'Flagstaff Gardens' },
      global: { stubs: { ElIcon: true, CameraCapture: true } },
    })
    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('Drop a pin here'))!
      .trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toBe('The pin could not be placed.')
    expect(wrapper.text()).not.toContain('/api/care/pins')
    expect(wrapper.emitted('pinned')).toBeUndefined()
    wrapper.unmount()
  })
})

it('places demo pins inside the selected area and emits the persisted coordinates', async () => {
  const bounds = { south: -37.82, north: -37.81, west: 144.95, east: 144.96 }
  vi.mocked(apiGet).mockResolvedValue([
    { coordinates: { lat: -37.815, lng: 144.955 } },
    { coordinates: { lat: -37.825, lng: 144.955 } },
  ])
  vi.mocked(createPin).mockImplementation(async (input) => ({
    ...input,
    id: 'demo-pin',
    hasPhoto: false,
    photoStatus: 'pending',
    createdAt: '2026-10-11',
  }))
  const wrapper = mount(PinTreeFlow, {
    props: { zoneId: 'area', landmark: 'Area', demo: true, area: { bounds } as never },
    global: { stubs: { ElIcon: true, CameraCapture: true } },
  })
  await wrapper.get('.primary-button').trigger('click')
  await flushPromises()
  const input = vi.mocked(createPin).mock.calls[0]![0]
  expect(input.latitude).toBeGreaterThanOrEqual(bounds.south)
  expect(input.latitude).toBeLessThanOrEqual(bounds.north)
  expect(input.longitude).toBeGreaterThanOrEqual(bounds.west)
  expect(input.longitude).toBeLessThanOrEqual(bounds.east)
  expect(wrapper.emitted('pinned')![0]![0]).toMatchObject({
    latitude: input.latitude,
    longitude: input.longitude,
  })
  await wrapper
    .findAll('button')
    .find((b) => b.text() === 'Write a message')!
    .trigger('click')
  await wrapper.get('textarea').setValue('Thank you tree')
  wrapper.vm.goToStep('pin')
  await flushPromises()
  wrapper.vm.goToStep('message')
  await flushPromises()
  expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('Thank you tree')
  expect(createPin).toHaveBeenCalledOnce()
  wrapper.unmount()
})

it('does not associate GPS outside the selected area with that area', async () => {
  vi.stubGlobal('navigator', {
    geolocation: { getCurrentPosition: (success: PositionCallback) => success(fix) },
  })
  const wrapper = mount(PinTreeFlow, {
    props: {
      zoneId: 'area',
      landmark: 'Area',
      area: { bounds: { south: -37.83, north: -37.82, west: 144.96, east: 144.97 } } as never,
    },
    global: { stubs: { ElIcon: true, CameraCapture: true } },
  })
  await wrapper.get('.primary-button').trigger('click')
  await flushPromises()
  expect(createPin).not.toHaveBeenCalled()
  expect(wrapper.get('[role="alert"]').text()).toContain('outside this area')
  wrapper.unmount()
})

it('warns about swear words, prevents posting, and clears the warning after editing', async () => {
  vi.stubGlobal('navigator', {
    geolocation: {
      getCurrentPosition: (success: PositionCallback) =>
        success({
          ...fix,
          coords: { ...fix.coords, accuracy: 5 },
        } as GeolocationPosition),
    },
  })
  vi.mocked(createPin).mockResolvedValue({
    id: 'pin',
    zoneId: 'area',
    latitude: -37.81,
    longitude: 144.95,
    accuracyM: 5,
    hasPhoto: false,
    photoStatus: 'pending',
    createdAt: '2026-10-11',
  })
  const wrapper = mount(PinTreeFlow, {
    props: { zoneId: 'area', landmark: 'Area' },
    global: { stubs: { ElIcon: true, CameraCapture: true } },
  })
  await wrapper.get('.primary-button').trigger('click')
  await flushPromises()
  await wrapper
    .findAll('button')
    .find((b) => b.text() === 'Write a message')!
    .trigger('click')
  await wrapper.get('textarea').setValue('fuck')
  expect(wrapper.get('#message-content-warning').text()).toContain('inappropriate language')
  expect(wrapper.get('textarea').attributes('aria-invalid')).toBe('true')
  expect(wrapper.get('.primary-button').attributes('disabled')).toBeDefined()
  await wrapper.get('.primary-button').trigger('click')
  expect(postMessage).not.toHaveBeenCalled()
  await wrapper.get('textarea').setValue('Thanks for the shade')
  expect(wrapper.find('#message-content-warning').exists()).toBe(false)
  expect(wrapper.get('.primary-button').attributes('disabled')).toBeUndefined()
  wrapper.unmount()
})
