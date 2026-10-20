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
import { useMemo } from "react";
import { qk } from "@/lib/query-keys";
import { getSettings } from "@/lib/api/settings";
import { putHomeLayout, type HomeLayout } from "@/lib/api/home";
import { getDef, type WidgetInstance } from "@/lib/widgets/registry";
import { getAccessToken } from "@/lib/auth/session";
import { ApiError } from "@/lib/api/errors";

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
  addWidget(defId: string, opts?: { props?: Record<string, unknown> }): void;
  removeWidget(instanceId: string): void;
  toggleCollapsed(instanceId: string): void;
  /** Persist new x/y/w/h coordinates from react-grid-layout. */
  applyLayout(
    items: Array<{ i: string; x: number; y: number; w: number; h: number }>,
  ): void;
  resetToDefault(): void;
}

export function useHomeLayout(): UseHomeLayoutResult {
  const qc = useQueryClient();
  const QUERY_KEY = qk.home.layout();

  const defaultLayout = useMemo(() => makeDefault(), []);

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
    if (!settings?.widgets || settings.widgets.length === 0)
      return defaultLayout;
    const norm = normaliseWidgets(settings.widgets as unknown);
    return norm && norm.length > 0 ? norm : defaultLayout;
  }, [settings, defaultLayout]);

  // Mirror the most recent widgets into a ref so queued mutations see the
  // latest optimistic state instead of a stale closure (delete then re-add
  // back-to-back would otherwise PUT against pre-delete widgets).
  const widgetsRef = React.useRef(widgets);
  React.useEffect(() => {
    widgetsRef.current = widgets;
  }, [widgets]);

  // Cache is the single source of truth for layout. We update it
  // optimistically on every change and persist to the server in the
  // background. We never touch the cache from server responses — that
  // raced with rapid drag/resize sequences and caused widgets to snap
  // back to stale positions whenever a slower in-flight PUT resolved
  // after a newer optimistic update.
  const mutation = useMutation({
    mutationFn: (newWidgets: WidgetInstance[]) => {
      if (!getAccessToken()) return Promise.resolve(null);
      return putHomeLayout({
        widgets: newWidgets as unknown as HomeLayout["widgets"],
      });
    },
    onError: (err) => {
      // Don't roll the cache back — newer optimistic updates may have
      // landed since this mutation started. 401s are handled by the
      // global auth-expired listener.
      if (!(err instanceof ApiError && err.status === 401)) {
        // eslint-disable-next-line no-console
        console.error("[useHomeLayout] mutation failed:", err);
      }
    },
  });

  function enqueue(next: WidgetInstance[]) {
    // Cache is authoritative. Update it synchronously so subsequent
    // reads see the new layout, then fire-and-forget the PUT.
    qc.setQueryData(QUERY_KEY, {
      widgets: next as unknown as HomeLayout["widgets"],
    });
    mutation.mutate(next);
  }

  function addWidget(
    defId: string,
    opts?: { props?: Record<string, unknown> },
  ) {
    const def = getDef(defId);
    const w = def?.defaultSize ?? 4;
    const h = def?.defaultH ?? 4;
    const current = widgetsRef.current;
    const maxY = current.reduce((m, x) => Math.max(m, x.y + x.h), 0);
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
    enqueue([...current, next]);
  }

  function removeWidget(instanceId: string) {
    enqueue(widgetsRef.current.filter((w) => w.id !== instanceId));
  }

  function toggleCollapsed(instanceId: string) {
    enqueue(
      widgetsRef.current.map((w) =>
        w.id === instanceId ? { ...w, collapsed: !w.collapsed } : w,
      ),
    );
  }

  function applyLayout(
    items: Array<{ i: string; x: number; y: number; w: number; h: number }>,
  ) {
    const byId = new Map(items.map((it) => [it.i, it]));
    const current = widgetsRef.current;
    const next = current.map((w) => {
      const it = byId.get(w.id);
      if (!it) return w;
      if (w.x === it.x && w.y === it.y && w.w === it.w && w.h === it.h)
        return w;
      return { ...w, x: it.x, y: it.y, w: it.w, h: it.h };
    });
    const changed = next.some((w, i) => w !== current[i]);
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
