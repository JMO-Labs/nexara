"use client";
/**
 * @file components/events/event-detail/useContainerRect.ts
 * @brief Tracks left/width of a container element (or the viewport).
 */
import * as React from "react";

/**
 * @brief Observe an element's horizontal rect; full viewport when no ref.
 * @param ref optional container ref
 * @return {left,width} or null until measured
 */
export function useContainerRect(
  ref: React.RefObject<HTMLElement | null> | undefined,
) {
  const [rect, setRect] = React.useState<{
    left: number;
    width: number;
  } | null>(null);
  React.useEffect(() => {
    if (!ref) {
      const update = () => setRect({ left: 0, width: window.innerWidth });
      update();
      window.addEventListener("resize", update);
      return () => window.removeEventListener("resize", update);
    }
    const el = ref.current;
    if (!el) return;
    const update = () => {
      const r = el.getBoundingClientRect();
      setRect({ left: r.left, width: r.width });
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      ro.disconnect();
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [ref]);
  return rect;
}
