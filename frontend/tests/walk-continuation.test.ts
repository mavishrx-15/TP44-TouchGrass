// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import WalkView from '@/views/WalkView.vue'
import GroundingSteps from '@/components/walk/GroundingSteps.vue'
import PinTreeFlow from '@/components/walk/PinTreeFlow.vue'
import StressCheckIn from '@/components/walk/StressCheckIn.vue'
import GoogleMapCanvas from '@/components/GoogleMapCanvas.vue'
import { useJourneyStore } from '@/stores/journey'
import { findAreas, growRoute } from '@/services/planning.service'
import { ApiError } from '@/api/client'
import { useRewardsStore } from '@/stores/rewards'
import { requestPersonalisedRoute } from '@/services/personalisation.service'
import type { PlannedRoute } from '@/types/planning'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/constants/zones', () => ({
  MELBOURNE_CENTER: { lat: -37.8136, lng: 144.9631 },
  loadAllZones: async () => ({ zones: [] }),
  getZoneFacts: async () => ({ treeCount: 40, topSpecies: [] }),
}))
vi.mock('@/services/care.service', () => ({ getApprovedMessages: async () => [] }))
vi.mock('@/services/planning.service', () => ({ growRoute: vi.fn(), findAreas: vi.fn() }))
vi.mock('@/services/personalisation.service', () => ({
  USE_MOCK_DATA: false,
  coverageFrom: () => null,
  deviceLocation: vi.fn(),
  loadPrecincts: async () => [],
  requestPersonalisedRoute: vi.fn(),
}))

const arrival = { lat: -37.81, lng: 144.95 }
const nextArea = {
  destination: {
    zoneId: 'next',
    label: 'Next grove',
    center: { lat: -37.812, lng: 144.952 },
    bounds: { north: -37.81, south: -37.813, east: 144.953, west: 144.951 },
    density: 'High' as const,
    treeCount: 45,
  },
  estimatedMinutes: 5,
  distanceMeters: 300,
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  sessionStorage.clear()
  vi.clearAllMocks()
  vi.mocked(findAreas).mockResolvedValue({ areas: [nextArea] })
})

describe('continuing a finished walk', () => {
  it('recommends and routes from the area just reached, excluding today’s visit', async () => {
    const journey = useJourneyStore()
    journey.startLocation = {
      id: 'original',
      label: 'Original start',
      coordinates: { lat: -37.82, lng: 144.96 },
    }
    journey.destination = { id: 'arrived', label: 'Arrived grove', coordinates: arrival }
    journey.sproutRoute = {
      encodedPolyline: '_p~iF~ps|U_ulLnnqC_mqNvxq`@',
      distanceMeters: 1000,
      durationMinutes: 12,
      denseZoneShare: 0.6,
      summaryChips: [],
      destination: { zoneId: 'arrived', label: 'Arrived grove', center: arrival, treeCount: 40 },
    } as PlannedRoute
    vi.mocked(growRoute)
      .mockRejectedValueOnce(new ApiError('POST /api/sprout/route failed', 502))
      .mockResolvedValue({
        origin: arrival,
        destination: nextArea.destination,
        durationMinutes: 5,
        distanceMeters: 300,
        encodedPolyline: '_p~iF~ps|U_ulLnnqC_mqNvxq`@',
        summaryChips: [],
        matches: [],
        steps: [],
        message: null,
        denseZoneShare: 0.7,
      })
    const wrapper = mount(WalkView, {
      global: {
        stubs: {
          RouterLink: true,
          GoogleMapCanvas: true,
          SproutTree: true,
          SproutWardrobe: true,
          VisitHistory: true,
          SproutLookPicker: true,
          GroundingSteps: true,
          PinTreeFlow: { name: 'PinTreeFlow', template: '<div />', methods: { goToStep() {} } },
          StressCheckIn: true,
          ElIcon: true,
        },
      },
    })
    try {
      await wrapper
        .findAll('button')
        .find((button) => button.text() === 'Walk without GPS')!
        .trigger('click')
      await wrapper
        .findAll('button')
        .find((button) => button.text() === 'I’ve arrived')!
        .trigger('click')
      await flushPromises()
      wrapper.findComponent(GroundingSteps).vm.$emit('done')
      await flushPromises()
      wrapper.findComponent(PinTreeFlow).vm.$emit('pinned', {
        id: 'saved-tree',
        latitude: -37.8102,
        longitude: 144.9502,
      })
      await flushPromises()
      expect(wrapper.findComponent(GoogleMapCanvas).props('ownPin')).toEqual({
        lat: -37.8102,
        lng: 144.9502,
      })
      wrapper.findComponent(PinTreeFlow).vm.$emit('done')
      await flushPromises()
      await wrapper
        .findAll('.walk-step')
        .find((button) => button.text().includes('Pin a tree'))!
        .trigger('click')
      await flushPromises()
      expect(wrapper.get('.walk-step[aria-current="step"]').text()).toContain('Pin a tree')
      await wrapper
        .findAll('.walk-step')
        .find((button) => button.text().includes('Check in'))!
        .trigger('click')
      await flushPromises()
      expect(wrapper.get('.walk-step[aria-current="step"]').text()).toContain('Check in')
      expect(wrapper.findComponent(GoogleMapCanvas).props('ownPin')).toEqual({
        lat: -37.8102,
        lng: 144.9502,
      })
      expect(
        wrapper
          .findAll('.walk-step')
          .find((button) => button.text().includes('Rewards'))!
          .attributes('disabled'),
      ).toBeDefined()
      const checkin = wrapper.findComponent(StressCheckIn)
      checkin.vm.$emit('log', 'calm')
      checkin.vm.$emit('log', 'calm')
      await flushPromises()
      expect(journey.startLocation.coordinates).toEqual(arrival)
      expect(findAreas).toHaveBeenLastCalledWith(arrival, expect.anything(), {
        excludedZoneIds: ['arrived'],
        limit: 3,
      })
      await wrapper.get('.nearby button.area').trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('The next route could not be loaded')
      expect(wrapper.text()).toContain('+5 leaf points')
      expect(journey.destination.id).toBe('arrived')
      expect(journey.sproutRoute?.destination.zoneId).toBe('arrived')
      expect(useRewardsStore().state.points).toBe(5)
      await wrapper.get('.nearby button.area').trigger('click')
      await flushPromises()
      expect(growRoute).toHaveBeenLastCalledWith(arrival, expect.anything(), undefined, 'next')
      expect(requestPersonalisedRoute).not.toHaveBeenCalled()
      expect(journey.destination.id).toBe('next')
      expect(wrapper.text()).toContain('70%')
    } finally {
      wrapper.unmount()
    }
  })
})
