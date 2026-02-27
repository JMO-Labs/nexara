/**
 * @file tests/components/feed/CommentThread.test.ts
 * @brief TDD tests for the CommentThread component.
 *
 * Verifies rendering of nested comments, author info, and
 * reply input functionality.
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CommentThread from '~/components/feed/CommentThread.vue'
import type { Comment } from '~/types/api'

const mockComments: Comment[] = [
  {
    id: 'c1',
    content: 'Great post!',
    author: { id: 'u1', username: 'bob', display_name: 'Bob', avatar_url: null },
    parent_id: null,
    created_at: '2026-02-26T11:00:00Z',
    replies: [
      {
        id: 'c2',
        content: 'Thanks!',
        author: { id: 'u2', username: 'alice', display_name: 'Alice', avatar_url: null },
        parent_id: 'c1',
        created_at: '2026-02-26T11:05:00Z',
        replies: [],
      },
    ],
  },
  {
    id: 'c3',
    content: 'Interesting perspective.',
    author: { id: 'u3', username: 'carol', display_name: 'Carol', avatar_url: null },
    parent_id: null,
    created_at: '2026-02-26T12:00:00Z',
    replies: [],
  },
]

describe('CommentThread', () => {
  it('renders top-level comments', () => {
    const wrapper = mount(CommentThread, {
      props: { comments: mockComments, postId: 'post-1' },
    })

    expect(wrapper.text()).toContain('Great post!')
    expect(wrapper.text()).toContain('Interesting perspective.')
  })

  it('renders nested replies', () => {
    const wrapper = mount(CommentThread, {
      props: { comments: mockComments, postId: 'post-1' },
    })

    expect(wrapper.text()).toContain('Thanks!')
  })

  it('displays comment author names', () => {
    const wrapper = mount(CommentThread, {
      props: { comments: mockComments, postId: 'post-1' },
    })

    expect(wrapper.text()).toContain('Bob')
    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('Carol')
  })

  it('emits add-comment when reply is submitted', async () => {
    const wrapper = mount(CommentThread, {
      props: { comments: mockComments, postId: 'post-1' },
    })

    const input = wrapper.find('[data-testid="comment-input"]')
    await input.setValue('My reply')

    const form = wrapper.find('[data-testid="comment-form"]')
    await form.trigger('submit')

    expect(wrapper.emitted('add-comment')).toBeTruthy()
    expect(wrapper.emitted('add-comment')![0]).toEqual([
      { postId: 'post-1', content: 'My reply', parentId: null },
    ])
  })

  it('renders empty state when no comments', () => {
    const wrapper = mount(CommentThread, {
      props: { comments: [], postId: 'post-1' },
    })

    const input = wrapper.find('[data-testid="comment-input"]')
    expect(input.exists()).toBe(true)
  })
})
