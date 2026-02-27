/**
 * @file tests/components/branding/CommunityLogo.test.ts
 * @brief TDD tests for the CommunityLogo component.
 *
 * Verifies dark-mode-aware logo rendering and text fallback behaviour.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import CommunityLogo from '~/components/branding/CommunityLogo.vue'

vi.mock('~/composables/useBranding', () => {
  const { ref, readonly } = require('vue')
  const branding = ref({
    community_name: 'TestCommunity',
    tagline: null,
    color_primary: '#3b82f6',
    color_primary_dark: '#2563eb',
    logo_light_url: null as string | null,
    logo_dark_url: null as string | null,
  })
  return {
    useBranding: () => ({
      branding: readonly(branding),
      loaded: readonly(ref(true)),
      fetchBranding: vi.fn(),
    }),
    __branding: branding,
  }
})

vi.mock('~/composables/useDarkMode', () => {
  const { ref } = require('vue')
  const isDark = ref(false)
  return {
    useDarkMode: () => ({ isDark, toggle: vi.fn() }),
    __isDark: isDark,
  }
})

describe('CommunityLogo', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows text fallback when no logo uploaded', () => {
    const wrapper = mount(CommunityLogo)

    expect(wrapper.find('span').text()).toBe('TestCommunity')
    expect(wrapper.find('img').exists()).toBe(false)
  })

  it('shows dark logo in dark mode when available', async () => {
    const { __branding } = await import('~/composables/useBranding') as any
    const { __isDark } = await import('~/composables/useDarkMode') as any

    __branding.value = {
      ...__branding.value,
      logo_light_url: '/light.png',
      logo_dark_url: '/dark.png',
    }
    __isDark.value = true

    const wrapper = mount(CommunityLogo)
    const img = wrapper.find('img')

    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('/dark.png')
  })
})
