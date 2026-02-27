/**
 * @file tests/components/branding/CommunityLogo.test.ts
 * @brief TDD tests for the CommunityLogo component.
 *
 * Verifies dark-mode-aware logo rendering and text fallback behaviour.
 */

import { ref, readonly } from 'vue'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import CommunityLogo from '~/components/branding/CommunityLogo.vue'

const brandingRef = ref({
  community_name: 'TestCommunity',
  tagline: null,
  color_primary: '#3b82f6',
  color_primary_dark: '#2563eb',
  logo_light_url: null as string | null,
  logo_dark_url: null as string | null,
})

const isDarkRef = ref(false)

vi.mock('~/composables/useBranding', () => ({
  useBranding: () => ({
    branding: readonly(brandingRef),
    loaded: readonly(ref(true)),
    fetchBranding: vi.fn(),
  }),
  __branding: brandingRef,
}))

vi.mock('~/composables/useDarkMode', () => ({
  useDarkMode: () => ({ isDark: isDarkRef, toggle: vi.fn() }),
  __isDark: isDarkRef,
}))

describe('CommunityLogo', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows text fallback when no logo uploaded', () => {
    const wrapper = mount(CommunityLogo)

    expect(wrapper.find('span').text()).toBe('TestCommunity')
    expect(wrapper.find('img').exists()).toBe(false)
  })

  it('shows dark logo in dark mode when available', () => {
    brandingRef.value = {
      ...brandingRef.value,
      logo_light_url: '/light.png',
      logo_dark_url: '/dark.png',
    }
    isDarkRef.value = true

    const wrapper = mount(CommunityLogo)
    const img = wrapper.find('img')

    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('/dark.png')
  })
})
