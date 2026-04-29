/**
 * @file tests/unit/hooks/useHomeLayout.test.tsx
 * @brief Unit tests for useHomeLayout hook.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

import * as settingsApi from '@/lib/api/settings';
import * as homeApi from '@/lib/api/home';
import { useHomeLayout } from '@/hooks/useHomeLayout';
import type { WidgetInstance } from '@/lib/widgets/registry';

vi.mock('@/lib/api/settings');
vi.mock('@/lib/api/home');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  Wrapper.displayName = 'Wrapper';
  return { Wrapper, qc };
}

function makeWidget(overrides: Partial<WidgetInstance> = {}): WidgetInstance {
  return {
    id: 'w-1',
    defId: 'feed',
    size: 'lg',
    collapsed: false,
    order: 0,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useHomeLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(homeApi.putHomeLayout).mockResolvedValue({});
  });

  describe('loading and default layout', () => {
    it('shows isLoading true initially, then resolves default layout when settings empty', async () => {
      vi.mocked(settingsApi.getSettings).mockResolvedValue({
        home_layout: null,
      } as unknown as ReturnType<typeof settingsApi.getSettings> extends Promise<infer T> ? T : never);

      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      // Default layout has 6 widgets
      expect(result.current.widgets.length).toBe(6);
      expect(result.current.widgets[0].defId).toBe('feed');
    });

    it('returns persisted widgets when home_layout is set', async () => {
      const persisted: WidgetInstance[] = [makeWidget()];
      vi.mocked(settingsApi.getSettings).mockResolvedValue({
        home_layout: { widgets: persisted },
      } as unknown as ReturnType<typeof settingsApi.getSettings> extends Promise<infer T> ? T : never);

      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.widgets).toEqual(persisted);
    });
  });

  describe('addWidget', () => {
    it('calls putHomeLayout with the appended widget', async () => {
      const existing = makeWidget({ id: 'existing', order: 0 });
      vi.mocked(settingsApi.getSettings).mockResolvedValue({
        home_layout: { widgets: [existing] },
      } as unknown as ReturnType<typeof settingsApi.getSettings> extends Promise<infer T> ? T : never);

      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      act(() => {
        result.current.addWidget('activity', { size: 'sm' });
      });

      await waitFor(() => expect(homeApi.putHomeLayout).toHaveBeenCalledTimes(1));

      const call = vi.mocked(homeApi.putHomeLayout).mock.calls[0][0];
      expect(call.widgets).toHaveLength(2);
      expect(call.widgets[1].defId).toBe('activity');
      expect(call.widgets[1].size).toBe('sm');
    });
  });

  describe('removeWidget', () => {
    it('calls putHomeLayout with the widget removed', async () => {
      const w1 = makeWidget({ id: 'w-1', order: 0 });
      const w2 = makeWidget({ id: 'w-2', defId: 'activity', order: 1 });
      vi.mocked(settingsApi.getSettings).mockResolvedValue({
        home_layout: { widgets: [w1, w2] },
      } as unknown as ReturnType<typeof settingsApi.getSettings> extends Promise<infer T> ? T : never);

      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      act(() => {
        result.current.removeWidget('w-1');
      });

      await waitFor(() => expect(homeApi.putHomeLayout).toHaveBeenCalledTimes(1));

      const call = vi.mocked(homeApi.putHomeLayout).mock.calls[0][0];
      expect(call.widgets).toHaveLength(1);
      expect(call.widgets[0].id).toBe('w-2');
    });
  });

  describe('toggleCollapsed', () => {
    it('flips collapsed state of the target widget', async () => {
      const w = makeWidget({ collapsed: false });
      vi.mocked(settingsApi.getSettings).mockResolvedValue({
        home_layout: { widgets: [w] },
      } as unknown as ReturnType<typeof settingsApi.getSettings> extends Promise<infer T> ? T : never);

      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      act(() => {
        result.current.toggleCollapsed('w-1');
      });

      await waitFor(() => expect(homeApi.putHomeLayout).toHaveBeenCalledTimes(1));

      const call = vi.mocked(homeApi.putHomeLayout).mock.calls[0][0];
      expect(call.widgets[0].collapsed).toBe(true);
    });
  });

  describe('reorder', () => {
    it('reorders widgets by provided id order', async () => {
      const w1 = makeWidget({ id: 'w-1', order: 0 });
      const w2 = makeWidget({ id: 'w-2', defId: 'activity', order: 1 });
      vi.mocked(settingsApi.getSettings).mockResolvedValue({
        home_layout: { widgets: [w1, w2] },
      } as unknown as ReturnType<typeof settingsApi.getSettings> extends Promise<infer T> ? T : never);

      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      act(() => {
        result.current.reorder(['w-2', 'w-1']);
      });

      await waitFor(() => expect(homeApi.putHomeLayout).toHaveBeenCalledTimes(1));

      const call = vi.mocked(homeApi.putHomeLayout).mock.calls[0][0];
      expect(call.widgets[0].id).toBe('w-2');
      expect(call.widgets[0].order).toBe(0);
      expect(call.widgets[1].id).toBe('w-1');
      expect(call.widgets[1].order).toBe(1);
    });
  });

  describe('setSize', () => {
    it('updates the size of the target widget', async () => {
      const w = makeWidget({ size: 'md' });
      vi.mocked(settingsApi.getSettings).mockResolvedValue({
        home_layout: { widgets: [w] },
      } as unknown as ReturnType<typeof settingsApi.getSettings> extends Promise<infer T> ? T : never);

      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      act(() => {
        result.current.setSize('w-1', 'full');
      });

      await waitFor(() => expect(homeApi.putHomeLayout).toHaveBeenCalledTimes(1));

      const call = vi.mocked(homeApi.putHomeLayout).mock.calls[0][0];
      expect(call.widgets[0].size).toBe('full');
    });
  });

  describe('resetToDefault', () => {
    it('resets layout to the 6-widget default', async () => {
      const w = makeWidget();
      vi.mocked(settingsApi.getSettings).mockResolvedValue({
        home_layout: { widgets: [w] },
      } as unknown as ReturnType<typeof settingsApi.getSettings> extends Promise<infer T> ? T : never);

      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      act(() => {
        result.current.resetToDefault();
      });

      await waitFor(() => expect(homeApi.putHomeLayout).toHaveBeenCalledTimes(1));

      const call = vi.mocked(homeApi.putHomeLayout).mock.calls[0][0];
      expect(call.widgets).toHaveLength(6);
      expect(call.widgets[0].defId).toBe('feed');
    });
  });

  describe('optimistic rollback on mutation error', () => {
    it('reverts to previous widgets when mutation errors', async () => {
      const w = makeWidget({ id: 'original' });
      vi.mocked(settingsApi.getSettings).mockResolvedValue({
        home_layout: { widgets: [w] },
      } as unknown as ReturnType<typeof settingsApi.getSettings> extends Promise<infer T> ? T : never);

      vi.mocked(homeApi.putHomeLayout).mockRejectedValue(new Error('network error'));

      const { Wrapper, qc } = createWrapper();
      const { result } = renderHook(() => useHomeLayout(), { wrapper: Wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      act(() => {
        result.current.removeWidget('original');
      });

      // After error, cache should be rolled back
      await waitFor(() => {
        const cached = qc.getQueryData<{ widgets: WidgetInstance[] } | null>(['home-layout']);
        // rolled back means the previous state (with 'original' widget) is restored
        expect(cached?.widgets ?? []).toEqual(expect.arrayContaining([expect.objectContaining({ id: 'original' })]));
      });
    });
  });
});
