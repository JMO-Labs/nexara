/**
 * @file tests/pages/admin/dashboard.test.ts
 * @brief Tests for the admin dashboard page.
 *
 * Verifies metrics cards render with data from /admin/metrics.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount  } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '~/stores/auth'
import AdminDashboard from '~/pages/app/admin/index.vue'
import MetricsCard from '~/components/admin/MetricsCard.vue'
import AuditLogTable from '~/components/admin/AuditLogTable.vue'
import type { User } from '~/types/api'

const mockAdminUser: User = {
  id: '1',
  email: 'admin@example.com',
  username: 'admin',
  display_name: 'Admin',
  email_verified: true,
  avatar_url: null,
  bio: null,
  pronouns: null,
  location: null,
  website_url: null,
  birthday: null,
  role: 'admin',
  totp_enabled: false,
  storage_used: 0,
  storage_quota: 1073741824,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  last_seen_at: null,
}

const mockMetrics = {
  total_users: 42,
  active_users_30d: 15,
  online_now: 3,
  total_posts: 120,
  posts_7d: 8,
  media_files: 45,
  storage_used_bytes: 1073741824,
  waf_blocks_total: 5,
}

const mockGet = vi.fn()

vi.mock('~/composables/useApi', () => ({
  useApi: () => ({ get: mockGet }),
}))

describe('Admin dashboard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    const authStore = useAuthStore()
    authStore.user = { ...mockAdminUser }
    mockGet
      .mockResolvedValueOnce(mockMetrics)
      .mockResolvedValueOnce({ items: [] })
  })

  it('renders metrics cards with data', async () => {
    const wrapper = mount(AdminDashboard, {
      global: {
        components: { AdminMetricsCard: MetricsCard, AdminAuditLogTable: AuditLogTable },
      },
    })
    await flushPromises()

    expect(mockGet).toHaveBeenCalledWith('/admin/metrics')
    expect(mockGet).toHaveBeenCalledWith('/admin/audit-log?limit=5')

    const cards = wrapper.findAllComponents(MetricsCard)
    expect(cards.length).toBeGreaterThanOrEqual(7)
    expect(wrapper.text()).toContain('42')
    expect(wrapper.text()).toContain('15')
    expect(wrapper.text()).toContain('3')
  })
})
