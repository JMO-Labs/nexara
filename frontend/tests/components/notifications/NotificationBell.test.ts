/**
 * @file tests/components/notifications/NotificationBell.test.ts
 * @brief TDD tests for the NotificationBell component.
 *
 * Verifies unread count badge visibility using a mocked Pinia store.
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import NotificationBell from '~/components/notifications/NotificationBell.vue'
import { useNotificationsStore } from '~/stores/notifications'

vi.mock('~/composables/useApi', () => ({
  useApi: () => ({
    get: vi.fn().mockResolvedValue({ count: 0 }),
    post: vi.fn().mockResolvedValue({}),
  }),
}))

describe('NotificationBell', () => {
  it('shows unread count badge when count > 0', () => {
    setActivePinia(createPinia())
    const store = useNotificationsStore()
    store.unreadCount = 5

    const wrapper = mount(NotificationBell, {
      global: { stubs: { teleport: true } },
    })

    const badge = wrapper.find('span')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe('5')
  })

  it('hides badge when count is 0', () => {
    setActivePinia(createPinia())
    const store = useNotificationsStore()
    store.unreadCount = 0

    const wrapper = mount(NotificationBell, {
      global: { stubs: { teleport: true } },
    })

    const badge = wrapper.find('span')
    expect(badge.exists()).toBe(false)
  })
})
