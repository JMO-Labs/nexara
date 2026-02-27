/**
 * @file tests/components/media/UploadZone.test.ts
 * @brief TDD tests for the UploadZone component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import UploadZone from '~/components/media/UploadZone.vue'

vi.mock('~/stores/auth', () => ({
  useAuthStore: () => ({ accessToken: 'test-token' }),
}))

describe('UploadZone', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('emits error when file exceeds size limit', async () => {
    const wrapper = mount(UploadZone)

    const bigFile = new File(['x'.repeat(100)], 'big.jpg', { type: 'image/jpeg' })
    Object.defineProperty(bigFile, 'size', { value: 25 * 1024 * 1024 })

    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [bigFile] })
    await input.trigger('change')

    expect(wrapper.emitted('error')).toBeTruthy()
    expect(wrapper.emitted('error')![0][0]).toContain('too large')
  })

  it('emits upload event on successful upload', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: '123', status: 'processing' }),
    } as Response)

    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:preview')

    const wrapper = mount(UploadZone)
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' })

    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')

    await vi.waitFor(() => {
      expect(wrapper.emitted('upload')).toBeTruthy()
    })
  })
})
