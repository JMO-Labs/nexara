/**
 * @file hooks/useHomeLayout.ts
 * @brief TanStack Query hook for persisted home page widget layout.
 *
 * Fetches layout from GET /api/v1/settings/ (home_layout key), merges with
 * a default when missing, and exposes mutation helpers with optimistic updates.
 */
'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { qk } from '@/lib/query-keys';
import { getSettings } from '@/lib/api/settings';
import { putHomeLayout, type HomeLayout } from '@/lib/api/home';
import type { WidgetInstance, WidgetSize } from '@/lib/widgets/registry';

// ---------------------------------------------------------------------------
// Default layout
// ---------------------------------------------------------------------------

function makeDefault(): WidgetInstance[] {
  const entries: Array<{ defId: string; size: WidgetSize; order: number }> = [
    { defId: 'feed', size: 'lg', order: 0 },
    { defId: 'upcoming-events', size: 'md', order: 1 },
    { defId: 'activity', size: 'sm', order: 2 },
    { defId: 'quick-actions', size: 'sm', order: 3 },
    { defId: 'media-carousel', size: 'full', order: 4 },
    { defId: 'my-groups', size: 'sm', order: 5 },
  ];
  return entries.map((e) => ({
    id: crypto.randomUUID(),
    defId: e.defId,
    size: e.size,
    order: e.order,
    collapsed: false,
  }));
}

// ---------------------------------------------------------------------------
// Public result type
// ---------------------------------------------------------------------------

export interface UseHomeLayoutResult {
  widgets: WidgetInstance[];
  isLoading: boolean;
  isError: boolean;
  /** Add a new widget instance to the layout. */
  addWidget(defId: string, opts?: { size?: WidgetSize; props?: unknown }): void;
  /** Remove a widget instance by its instance id. */
  removeWidget(instanceId: string): void;
  /** Toggle the collapsed state of a widget instance. */
  toggleCollapsed(instanceId: string): void;
  /** Reorder widgets by providing instance ids in the desired order. */
  reorder(instanceIds: string[]): void;
  /** Change the size of a widget instance. */
  setSize(instanceId: string, size: WidgetSize): void;
  /** Reset the layout to the built-in default. */
  resetToDefault(): void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * @brief Hook that provides the persisted home layout and mutation helpers.
 *
 * Reads from the settings endpoint (home_layout key). Falls back to a default
 * layout when the key is absent. Mutations are optimistic with rollback.
 *
 * @return UseHomeLayoutResult with widget array and action helpers.
 */
export function useHomeLayout(): UseHomeLayoutResult {
  const qc = useQueryClient();
  const QUERY_KEY = qk.home.layout();

  // Fetch the raw settings; extract home_layout from it.
  const {
    data: settings,
    isLoading,
    isError,
  } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const s = await getSettings();
      // settings.home_layout may be null/undefined or a HomeLayout-shaped dict
      return (s as unknown as { home_layout?: HomeLayout | null }).home_layout ?? null;
    },
    staleTime: 60_000,
  });

  const widgets: WidgetInstance[] =
    settings?.widgets && settings.widgets.length > 0 ? settings.widgets : makeDefault();

  // ---------------------------------------------------------------------------
  // Single base mutation — PATCHes settings with a new widget list
  // ---------------------------------------------------------------------------
  const mutation = useMutation({
    mutationFn: (newWidgets: WidgetInstance[]) =>
      putHomeLayout({ widgets: newWidgets }),

    onMutate: async (newWidgets) => {
      await qc.cancelQueries({ queryKey: QUERY_KEY });
      const previous = qc.getQueryData<HomeLayout | null>(QUERY_KEY);
      qc.setQueryData(QUERY_KEY, { widgets: newWidgets });
      return { previous };
    },

    onError: (_err, _vars, ctx) => {
      if (ctx?.previous !== undefined) {
        qc.setQueryData(QUERY_KEY, ctx.previous);
      }
    },

    onSettled: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });

  function mutate(newWidgets: WidgetInstance[]) {
    mutation.mutate(newWidgets);
  }

  // ---------------------------------------------------------------------------
  // Public helpers
  // ---------------------------------------------------------------------------

  function addWidget(defId: string, opts?: { size?: WidgetSize; props?: unknown }) {
    const next: WidgetInstance = {
      id: crypto.randomUUID(),
      defId,
      size: opts?.size ?? 'md',
      collapsed: false,
      order: widgets.length,
      props: opts?.props,
    };
    mutate([...widgets, next]);
  }

  function removeWidget(instanceId: string) {
    mutate(widgets.filter((w) => w.id !== instanceId));
  }

  function toggleCollapsed(instanceId: string) {
    mutate(widgets.map((w) => (w.id === instanceId ? { ...w, collapsed: !w.collapsed } : w)));
  }

  function reorder(instanceIds: string[]) {
    const byId = new Map(widgets.map((w) => [w.id, w]));
    const reordered = instanceIds
      .map((id, idx) => {
        const w = byId.get(id);
        return w ? { ...w, order: idx } : null;
      })
      .filter((w): w is WidgetInstance => w !== null);
    mutate(reordered);
  }

  function setSize(instanceId: string, size: WidgetSize) {
    mutate(widgets.map((w) => (w.id === instanceId ? { ...w, size } : w)));
  }

  function resetToDefault() {
    mutate(makeDefault());
  }

  return {
    widgets,
    isLoading,
    isError,
    addWidget,
    removeWidget,
    toggleCollapsed,
    reorder,
    setSize,
    resetToDefault,
  };
}
