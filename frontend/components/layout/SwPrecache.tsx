"use client";
/**
 * @file components/layout/SwPrecache.tsx
 * @brief Mounted under /app: lets the SW cache this page and its assets for
 *        offline use (see lib/pwa/precache). Renders nothing.
 */
import { useEffect } from "react";
import { startPrecache } from "@/lib/pwa/precache";

/** @return null */
export function SwPrecache() {
  useEffect(() => startPrecache(), []);
  return null;
}
