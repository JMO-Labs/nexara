/**
 * @file tests/components/media/MediaLightbox.test.ts
 * @brief TDD tests for the MediaLightbox component.
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MediaLightbox from '~/components/media/MediaLightbox.vue'

const mockItems = [
  { id: '1', url: '/img/1.jpg', thumbnail_url: '/thumb/1.jpg', mime_type: 'image/jpeg', width: 800, height: 600 },
  { id: '2', url: '/img/2.jpg', thumbnail_url: '/thumb/2.jpg', mime_type: 'image/png', width: 640, height: 480 },
]

describe('MediaLightbox', () => {
  it('renders the lightbox dialog in the body', () => {
    mount(MediaLightbox, {
      props: { items: mockItems, startIndex: 0 },
    })

    const img = document.body.querySelector('img')
    expect(img).not.toBeNull()
    expect(img?.getAttribute('src')).toBe('/img/1.jpg')
  })

  it('emits close on escape key', async () => {
    const wrapper = mount(MediaLightbox, {
      props: { items: mockItems, startIndex: 0 },
    })

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))

    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
