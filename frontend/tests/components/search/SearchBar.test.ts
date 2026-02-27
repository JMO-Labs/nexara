/**
 * @file tests/components/search/SearchBar.test.ts
 * @brief Tests for SearchBar component.
 *
 * Verifies debounced input and navigation to search page on submit.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import SearchBar from '~/components/search/SearchBar.vue'

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
}))

describe('SearchBar', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockPush.mockClear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('debounces input', async () => {
    const wrapper = mount(SearchBar)
    const input = wrapper.find('#search-input')

    await input.setValue('hello')
    expect(mockPush).not.toHaveBeenCalled()

    vi.advanceTimersByTime(300)
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['hello'])
  })

  it('navigates to search page on form submit', async () => {
    const wrapper = mount(SearchBar)
    const input = wrapper.find('#search-input')
    await input.setValue('test query')

    await wrapper.find('form').trigger('submit.prevent')

    expect(mockPush).toHaveBeenCalledWith({ path: '/app/search', query: { q: 'test query' } })
  })
})
