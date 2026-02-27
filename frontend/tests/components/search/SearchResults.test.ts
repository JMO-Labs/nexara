/**
 * @file tests/components/search/SearchResults.test.ts
 * @brief Tests for SearchResults component.
 *
 * Verifies rendering of tabbed results and empty state.
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SearchResults from '~/components/search/SearchResults.vue'
import type { SearchResultItem } from '~/types/api'

const mockItems: SearchResultItem[] = [
  {
    id: '1',
    type: 'posts',
    title: 'First post',
    snippet: 'Some content here',
    created_at: '2026-02-26T10:00:00Z',
  },
  {
    id: '2',
    type: 'users',
    title: 'Alice',
    snippet: 'Developer',
    created_at: '2026-02-25T12:00:00Z',
  },
]

describe('SearchResults', () => {
  it('renders tabbed results with items', () => {
    const wrapper = mount(SearchResults, {
      props: { items: mockItems, activeTab: 'all' },
    })

    expect(wrapper.find('ul[role="list"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('First post')
    expect(wrapper.text()).toContain('Some content here')
    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('Developer')
  })

  it('shows empty state when no results', () => {
    const wrapper = mount(SearchResults, {
      props: { items: [], activeTab: 'posts' },
    })

    expect(wrapper.find('ul[role="list"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('search.noResults')
  })
})
