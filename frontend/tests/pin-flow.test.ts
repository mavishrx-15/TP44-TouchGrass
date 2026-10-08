// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PinTreeFlow from '@/components/walk/PinTreeFlow.vue'
import { createPin } from '@/services/care.service'
import { ApiError } from '@/api/client'

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
    wrapper.unmount()
  })
})
