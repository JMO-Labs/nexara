/**
 * @file tests/pages/settings/notifications.test.ts
 * @brief Tests for the notification preferences tab.
 *
 * Verifies matrix table render (rows = types, cols = In-app/Email)
 * and checkbox toggle behavior bound to notification preferences.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount  } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useSettingsStore } from '~/stores/settings'
import type { UserSettingsResponse } from '~/types/api'
import NotificationsSettings from '~/pages/app/settings/notifications.vue'

const mockSettings: UserSettingsResponse = {
  notif_mention_inapp: true,
  notif_mention_email: false,
  notif_comment_inapp: true,
  notif_comment_email: true,
  notif_reaction_inapp: false,
  notif_reaction_email: false,
  notif_new_post_inapp: true,
  notif_new_post_email: false,
  notif_system_inapp: true,
  notif_system_email: false,
  notif_invite_accepted_inapp: false,
  notif_invite_accepted_email: false,
  mute_all_email: false,
  theme: 'system',
  locale: 'en-US',
}

const mockGet = vi.fn()
const mockPut = vi.fn()

vi.mock('~/composables/useApi', () => ({
  useApi: () => ({
    get: mockGet,
    put: mockPut,
    post: mockPut,
    del: vi.fn(),
  }),
}))

describe('Notifications settings', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockGet.mockResolvedValue(mockSettings)
  })

  it('renders matrix table with notification types and channels', async () => {
    const wrapper = mount(NotificationsSettings)
    await wrapper.vm.$nextTick()

    const table = wrapper.find('table')
    expect(table.exists()).toBe(true)
    expect(table.find('thead').exists()).toBe(true)
    expect(table.find('tbody').exists()).toBe(true)
  })

  it('renders checkboxes for each notification type (in-app and email)', async () => {
    const store = useSettingsStore()
    store.settings = { ...mockSettings }

    const wrapper = mount(NotificationsSettings)
    await wrapper.vm.$nextTick()

    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    expect(checkboxes.length).toBeGreaterThanOrEqual(6)
  })

  it('calls fetchSettings on mount', async () => {
    const store = useSettingsStore()
    const fetchSpy = vi.spyOn(store, 'fetchSettings').mockResolvedValue()

    mount(NotificationsSettings)
    await vi.waitFor(() => expect(fetchSpy).toHaveBeenCalled())
  })

  it('calls updateNotificationPreferences when save is clicked', async () => {
    const store = useSettingsStore()
    store.settings = { ...mockSettings }
    const updateSpy = vi.spyOn(store, 'updateNotificationPreferences').mockResolvedValue()

    const wrapper = mount(NotificationsSettings)
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const saveButton = buttons[buttons.length - 1]
    await saveButton.trigger('click')
    await flushPromises()

    expect(updateSpy).toHaveBeenCalled()
  })
})
