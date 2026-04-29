/**
 * @file hooks/useHomeLayout.ts
 * @brief TanStack Query hook for the persisted home page widget layout.
 *        Layout uses react-grid-layout coordinates (x, y, w, h).
 *        Reads from GET /api/v1/settings/ (home_layout key); persists via
 *        the same endpoint with optimistic updates and a serialised mutation
 *        queue so rapid drags / resizes don't race.
 */
"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef } from "react";
import { qk } from "@/lib/query-keys";
import { getSettings } from "@/lib/api/settings";
import { putHomeLayout, type HomeLayout } from "@/lib/api/home";
import { getDef, type WidgetInstance } from "@/lib/widgets/registry";

// ---------------------------------------------------------------------------
// Default layout — compact 12-col dashboard
// ---------------------------------------------------------------------------

interface DefEntry {
  defId: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

// Row 0: action-menu strip — quick-actions | activity | my-groups (equal height)
// Row 1: feed (8) | upcoming-events (4)
// Row 2: media-carousel (12)
const DEFAULT_ENTRIES: DefEntry[] = [
  { defId: "quick-actions", x: 0, y: 0, w: 4, h: 3 },
  { defId: "activity", x: 4, y: 0, w: 4, h: 3 },
  { defId: "my-groups", x: 8, y: 0, w: 4, h: 3 },
  { defId: "feed", x: 0, y: 3, w: 8, h: 8 },
  { defId: "upcoming-events", x: 8, y: 3, w: 4, h: 8 },
  { defId: "media-carousel", x: 0, y: 11, w: 12, h: 4 },
];

function makeDefault(): WidgetInstance[] {
  return DEFAULT_ENTRIES.map((e) => ({
    id: crypto.randomUUID(),
    defId: e.defId,
    x: e.x,
    y: e.y,
    w: e.w,
    h: e.h,
    collapsed: false,
  }));
}

// ---------------------------------------------------------------------------
// Legacy normalisation — convert old {size, order} rows to {x, y, w, h}.
// ---------------------------------------------------------------------------

const LEGACY_W: Record<string, number> = { sm: 3, md: 4, lg: 8, full: 12 };
function legacyW(value: unknown): number {
  if (typeof value === "number") return Math.max(1, Math.min(12, value));
  if (typeof value === "string" && value in LEGACY_W) return LEGACY_W[value];
  return 4;
}

function normaliseWidgets(raw: unknown): WidgetInstance[] | null {
  if (!Array.isArray(raw)) return null;
  // Detect new shape (has x/y/w/h) vs legacy (has size/order).
  const isNew = raw.every(
    (w) =>
      typeof w === "object" &&
      w !== null &&
      "w" in w &&
      "h" in w &&
      "x" in w &&
      "y" in w,
  );
  if (isNew) {
    return raw.map((w) => {
      const r = w as Record<string, unknown>;
      return {
        id: String(r.id ?? crypto.randomUUID()),
        defId: String(r.defId ?? r.def_id ?? ""),
        x: Number(r.x) || 0,
        y: Number(r.y) || 0,
        w: Math.max(1, Math.min(12, Number(r.w) || 4)),
        h: Math.max(1, Number(r.h) || 4),
        collapsed: Boolean(r.collapsed),
        props: (r.props as Record<string, unknown> | undefined) ?? undefined,
      };
    });
  }
  // Legacy: pack rows by `order` using width from `size`.
  let cursorX = 0;
  let cursorY = 0;
  return raw.map((w, i) => {
    const r = w as Record<string, unknown>;
    const width = legacyW(r.size);
    if (cursorX + width > 12) {
      cursorX = 0;
      cursorY += 4;
    }
    const item: WidgetInstance = {
      id: String(r.id ?? crypto.randomUUID()),
      defId: String(r.defId ?? r.def_id ?? ""),
      x: cursorX,
      y: cursorY,
      w: width,
      h: 4,
      collapsed: Boolean(r.collapsed),
      props: (r.props as Record<string, unknown> | undefined) ?? undefined,
    };
    cursorX += width;
    void i;
    return item;
  });
}

// ---------------------------------------------------------------------------

export interface UseHomeLayoutResult {
  widgets: WidgetInstance[];
  isLoading: boolean;
  isError: boolean;
  addWidget(
    defId: string,
    opts?: { props?: Record<string, unknown> },
  ): void;
  removeWidget(instanceId: string): void;
  toggleCollapsed(instanceId: string): void;
  /** Persist new x/y/w/h coordinates from react-grid-layout. */
  applyLayout(items: Array<{ i: string; x: number; y: number; w: number; h: number }>): void;
  resetToDefault(): void;
}

export function useHomeLayout(): UseHomeLayoutResult {
  const qc = useQueryClient();
  const QUERY_KEY = qk.home.layout();

  const defaultLayout = useMemo(() => makeDefault(), []);
  const pendingRef = useRef<Promise<unknown>>(Promise.resolve());

  const {
    data: settings,
    isLoading,
    isError,
  } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const s = await getSettings();
      return (
        (s as unknown as { home_layout?: HomeLayout | null }).home_layout ??
        null
      );
    },
    staleTime: 60_000,
  });

  const widgets: WidgetInstance[] = React.useMemo(() => {
    if (!settings?.widgets || settings.widgets.length === 0) return defaultLayout;
    const norm = normaliseWidgets(settings.widgets as unknown);
    return norm && norm.length > 0 ? norm : defaultLayout;
  }, [settings, defaultLayout]);

  const mutation = useMutation({
    mutationFn: (newWidgets: WidgetInstance[]) =>
      putHomeLayout({ widgets: newWidgets as unknown as HomeLayout["widgets"] }),
    onMutate: async (newWidgets) => {
      await qc.cancelQueries({ queryKey: QUERY_KEY });
      const previous = qc.getQueryData<HomeLayout | null>(QUERY_KEY);
      qc.setQueryData(QUERY_KEY, {
        widgets: newWidgets as unknown as HomeLayout["widgets"],
      });
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous !== undefined) qc.setQueryData(QUERY_KEY, ctx.previous);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });

  function enqueue(next: WidgetInstance[]) {
    pendingRef.current = pendingRef.current
      .catch(() => undefined)
      .then(() => mutation.mutateAsync(next))
      .catch(() => undefined);
  }

  function addWidget(
    defId: string,
    opts?: { props?: Record<string, unknown> },
  ) {
    const def = getDef(defId);
    const w = def?.defaultSize ?? 4;
    const h = def?.defaultH ?? 4;
    // Place new widget below the current layout to avoid overlaps.
    const maxY = widgets.reduce((m, x) => Math.max(m, x.y + x.h), 0);
    const next: WidgetInstance = {
      id: crypto.randomUUID(),
      defId,
      x: 0,
      y: maxY,
      w,
      h,
      collapsed: false,
      props: opts?.props,
    };
    enqueue([...widgets, next]);
  }

  function removeWidget(instanceId: string) {
    enqueue(widgets.filter((w) => w.id !== instanceId));
  }

  function toggleCollapsed(instanceId: string) {
    enqueue(
      widgets.map((w) =>
        w.id === instanceId ? { ...w, collapsed: !w.collapsed } : w,
      ),
    );
  }

  function applyLayout(
    items: Array<{ i: string; x: number; y: number; w: number; h: number }>,
  ) {
    const byId = new Map(items.map((it) => [it.i, it]));
    const next = widgets.map((w) => {
      const it = byId.get(w.id);
      if (!it) return w;
      if (w.x === it.x && w.y === it.y && w.w === it.w && w.h === it.h) return w;
      return { ...w, x: it.x, y: it.y, w: it.w, h: it.h };
    });
    // Skip mutation if nothing changed.
    const changed = next.some((w, i) => w !== widgets[i]);
    if (!changed) return;
    enqueue(next);
  }

  function resetToDefault() {
    enqueue(makeDefault());
  }

  return {
    widgets,
    isLoading,
    isError,
    addWidget,
    removeWidget,
    toggleCollapsed,
    applyLayout,
    resetToDefault,
  };
}
