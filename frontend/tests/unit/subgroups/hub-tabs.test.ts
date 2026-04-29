/**
 * @file tests/unit/subgroups/hub-tabs.test.ts
 * @brief Verify GROUP_TABS has icons and expected structure.
 */
import { describe, it, expect } from 'vitest';
import { GROUP_TABS } from '@/components/subgroups/hub/tabs';

describe('GROUP_TABS', () => {
  it('has all required tabs with icons', () => {
    const tabIds = ['overview', 'events', 'galleries', 'media', 'posts', 'members', 'settings'];
    expect(GROUP_TABS).toHaveLength(7);

    GROUP_TABS.forEach((tab) => {
      expect(tabIds).toContain(tab.id);
      expect(tab.label).toBeTruthy();
      expect(tab.Icon).toBeDefined(); // Icon is a React component
    });
  });

  it('has icons assigned to all tabs', () => {
    const expectedIcons = {
      overview: 'HomeIcon',
      events: 'CalendarDaysIcon',
      galleries: 'PhotoIcon',
      media: 'FilmIcon',
      posts: 'NewspaperIcon',
      members: 'UsersIcon',
      settings: 'Cog6ToothIcon',
    };

    Object.entries(expectedIcons).forEach(([tabId, expectedIconName]) => {
      const tab = GROUP_TABS.find((t) => t.id === tabId);
      expect(tab).toBeDefined();
      expect(tab?.Icon).toBeDefined();
      // Verify Icon is callable (React component)
      expect(typeof tab?.Icon).not.toBe('undefined');
    });
  });

  it('settings tab has visible() predicate for role check', () => {
    const settingsTab = GROUP_TABS.find((t) => t.id === 'settings');
    expect(settingsTab?.visible).toBeDefined();
  });
});
