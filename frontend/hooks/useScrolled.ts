"use client";
/**
 * @file hooks/useScrolled.ts
 * @brief True once the window has scrolled past a few pixels.
 */
import { useEffect, useState } from "react";

/**
 * @brief Track whether the page is scrolled.
 * @param threshold px before it counts as scrolled
 * @return scrolled flag
 */
export function useScrolled(threshold = 8): boolean {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > threshold);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [threshold]);
  return scrolled;
}
