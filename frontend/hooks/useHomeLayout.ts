/**
 * @file hooks/useHomeLayout.ts
 * @brief Persisted home widget column prefs ({order, hidden}) from settings
 *        `home_layout`. Optimistic cache updates; PUT debounced 500ms.
 */
"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getSettings } from "@/lib/api/settings";
import { putHomeLayout, type HomeLayout } from "@/lib/api/home";
import type { WidgetId } from "@/components/home/widgetRegistry";

/** Default order; keep in sync with WIDGETS in widgetRegistry.tsx. */
const IDS: string[] = [
  "upcoming-events",
  "my-groups",
  "media",
  "quick-actions",
];
const DEBOUNCE_MS = 500;

const DEFAULTS = (): { order: WidgetId[]; hidden: WidgetId[] } => ({
  order: IDS.slice() as WidgetId[],
  hidden: [],
});

/**
 * @brief Coerce stored value to a valid layout; any other shape -> defaults.
 * @param raw stored home_layout value
 * @return normalised order/hidden
 */
function normalise(raw: unknown): { order: WidgetId[]; hidden: WidgetId[] } {
  const r = raw as { order?: unknown; hidden?: unknown } | null;
  if (!r || !Array.isArray(r.order) || !Array.isArray(r.hidden))
    return DEFAULTS();
  const known = (a: unknown[]) =>
    a.filter(
      (x, i): x is WidgetId => IDS.includes(x as string) && a.indexOf(x) === i,
    );
  const order = known(r.order);
  return {
    order: [
      ...order,
      ...IDS.filter((id) => !order.includes(id as WidgetId)),
    ] as WidgetId[],
    hidden: known(r.hidden),
  };
}

export interface UseHomeLayoutResult {
  order: WidgetId[];
  hidden: WidgetId[];
  move(from: number, to: number): void;
  toggle(id: WidgetId): void;
}

/**
 * @brief Read and edit the widget column layout.
 * @return order, hidden, move, toggle
 */
export function useHomeLayout(): UseHomeLayoutResult {
  const qc = useQueryClient();
  const key = React.useMemo(() => qk.home.layout(), []);
  const { data } = useQuery({
    queryKey: key,
    queryFn: async () =>
      (await getSettings()) as unknown as { home_layout?: unknown },
    select: (s) => normalise(s?.home_layout),
    staleTime: 60_000,
  });
  const layout = data ?? DEFAULTS();
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const current = React.useCallback(
    () =>
      normalise(
        (qc.getQueryData(key) as { home_layout?: unknown } | undefined)
          ?.home_layout,
      ),
    [qc, key],
  );

  const flush = React.useCallback(() => {
    timer.current = null;
    const l: HomeLayout = current();
    putHomeLayout(l).catch(() => {});
  }, [current]);

  React.useEffect(
    () => () => {
      if (timer.current) {
        clearTimeout(timer.current);
        flush();
      }
    },
    [flush],
  );

  const save = (next: { order: WidgetId[]; hidden: WidgetId[] }) => {
    qc.setQueryData(key, { home_layout: next });
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(flush, DEBOUNCE_MS);
  };

  return {
    ...layout,
    move(from, to) {
      const order = current().order.slice();
      if (from === to || !order[from] || to < 0 || to >= order.length) return;
      order.splice(to, 0, order.splice(from, 1)[0]);
      save({ ...current(), order });
    },
    toggle(id) {
      const { hidden } = current();
      save({
        ...current(),
        hidden: hidden.includes(id)
          ? hidden.filter((h) => h !== id)
          : [...hidden, id],
      });
    },
  };
}
