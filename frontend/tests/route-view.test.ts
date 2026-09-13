import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PersonalisedRouteView from '@/views/PersonalisedRouteView.vue'
import { getWalkingRoutes } from '@/services/discovery.service'
import { useJourneyStore } from '@/stores/journey'
import type { RouteOption } from '@/types/discovery'
vi.mock('@/services/discovery.service', async (importOriginal) => ({
  ...(await importOriginal<object>()),
  getWalkingRoutes: vi.fn(),
}))
afterEach(() => vi.clearAllMocks())
const route: RouteOption = {
  id: 'recommended',
  label: 'Your personalised route',
  bestMatch: true,
  message: 'Best available match',
  explanation: ['Park trees match your priorities'],
  matchScore: 0.8,
  scores: { canopy: 1, shade: 0.8, noise: 0.8, allergy: 1 },
  travelMode: 'WALK',
  withinTimeBudget: true,
  durationMinutes: 10,
  distanceKm: 1,
  treeCount: 50,
}
it('calculates one route with the shared origin, recalculates transport and clears stale results', async () => {
  const pinia = createPinia()
  setActivePinia(pinia)
  const journey = useJourneyStore()
  journey.precincts = [
    {
      id: 'test',
      name: 'Test',
      referencePoint: { lat: -37.795, lng: 144.915 },
      treeCount: 100,
      zoneCount: 1,
      speciesCount: 1,
    },
  ]
  journey.setStart({
    id: 'start',
    label: 'Chosen home origin',
    coordinates: journey.precincts[0]!.referencePoint,
  })
  journey.destination = {
    id: 'end',
    label: 'Chosen destination',
    coordinates: { lat: -37.8, lng: 144.92 },
  }
  vi.mocked(getWalkingRoutes).mockResolvedValue([route])
  const wrapper = mount(PersonalisedRouteView, {
    global: {
      plugins: [pinia],
      stubs: {
        AppHeader: true,
        GoogleMapCanvas: true,
        LocationSearch: true,
        RouterLink: true,
        ElTag: true,
        ElRadioGroup: true,
        ElRadioButton: true,
        ElButton: true,
        ElAlert: true,
      },
    },
  })
  await flushPromises()
  expect(getWalkingRoutes).toHaveBeenLastCalledWith(
    journey.startLocation,
    journey.destination.coordinates,
    journey.preferences,
    'WALK',
    expect.any(AbortSignal),
  )
  expect(wrapper.findAll('[aria-label="Recommended route"]')).toHaveLength(1)
  expect(wrapper.text()).toContain('Why This Route?')
  journey.travelMode = 'TRANSIT'
  await flushPromises()
  expect(getWalkingRoutes).toHaveBeenLastCalledWith(
    journey.startLocation,
    journey.destination.coordinates,
    journey.preferences,
    'TRANSIT',
    expect.any(AbortSignal),
  )
  expect(wrapper.find('a.navigation-link').attributes('href')).toContain('travelmode=transit')
  let resolve!: (value: RouteOption[]) => void
  vi.mocked(getWalkingRoutes).mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done
      }),
  )
  journey.setStart({
    id: 'new',
    label: 'Changed origin',
    coordinates: { lat: -37.796, lng: 144.916 },
  })
  await flushPromises()
  journey.setStart(null)
  await flushPromises()
  resolve([route])
  await flushPromises()
  expect(wrapper.findAll('[aria-label="Recommended route"]')).toHaveLength(0)
  expect(wrapper.find('a.navigation-link').exists()).toBe(false)
  wrapper.unmount()
})
