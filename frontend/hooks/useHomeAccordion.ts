"use client";
/**
 * @file hooks/useHomeAccordion.ts
 * @brief Single-open accordion state for the phone home tiles.
 */
import * as React from "react";

export type TileId = "next" | "chat" | "photos" | "feed";

/**
 * @brief Track which home tile is open.
 * @param defaultOpen Initially open tile, or null.
 * @return open tile id and toggle (re-toggling the open tile closes it)
 */
export function useHomeAccordion(defaultOpen: TileId | null) {
  const [open, setOpen] = React.useState<TileId | null>(defaultOpen);
  const toggle = React.useCallback(
    (id: TileId) => setOpen((cur) => (cur === id ? null : id)),
    [],
  );
  return { open, toggle };
}
