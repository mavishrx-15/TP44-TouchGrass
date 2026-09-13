import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import LocationSearch from '@/components/LocationSearch.vue'
import { getPlaceDetails, getPlaceSuggestions } from '@/services/discovery.service'
vi.mock('@/services/discovery.service', () => ({
  getPlaceSuggestions: vi.fn(),
  getPlaceDetails: vi.fn(),
}))
afterEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
})
const stubs = {
  ElInput: {
    props: ['modelValue'],
    template:
      '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
}
it('debounces autocomplete and ignores responses for an older query', async () => {
  vi.useFakeTimers()
  let resolveOld!: (value: { id: string; label: string }[]) => void
  vi.mocked(getPlaceSuggestions)
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve
        }),
    )
    .mockResolvedValueOnce([{ id: 'new', label: 'New Place' }])
  const wrapper = mount(LocationSearch, {
    props: { label: 'Starting location', modelValue: null },
    global: { stubs },
  })
  await wrapper.find('input').setValue('old')
  expect(getPlaceSuggestions).not.toHaveBeenCalled()
  await vi.advanceTimersByTimeAsync(250)
  await wrapper.find('input').setValue('new')
  await vi.advanceTimersByTimeAsync(250)
  resolveOld([{ id: 'old', label: 'Old Place' }])
  await flushPromises()
  expect(wrapper.text()).toContain('New Place')
  expect(wrapper.text()).not.toContain('Old Place')
  vi.mocked(getPlaceDetails).mockResolvedValue({
    id: 'new',
    label: 'New Place',
    coordinates: { lat: 1, lng: 2 },
  })
  await wrapper
    .findAll('button')
    .find((b) => b.text() === 'New Place')!
    .trigger('click')
  await flushPromises()
  expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toMatchObject({
    label: 'New Place',
    coordinates: { lat: 1, lng: 2 },
  })
  wrapper.unmount()
})
