"use client";
/**
 * @file hooks/useScrollDirection.ts
 * @brief Window scroll direction with a "scrolled past" threshold.
 */
import { useEffect, useState } from "react";

/**
 * @brief Track scroll direction.
 * @param threshold px scrolled before "down" can be reported
 * @return "down" once past threshold while scrolling down, else "up"
 */
export function useScrollDirection(threshold = 80): "up" | "down" {
  const [dir, setDir] = useState<"up" | "down">("up");
  useEffect(() => {
    let last = window.scrollY;
    const onScroll = () => {
      const y = window.scrollY;
      if (y < last) setDir("up");
      else if (y > threshold && y > last) setDir("down");
      last = y;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [threshold]);
  return dir;
}
