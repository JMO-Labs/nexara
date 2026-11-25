"use client";
/**
 * @file hooks/useFillHeight.ts
 * @brief Publish the viewport height left below an element as a CSS variable
 *        (e.g. `--bento-h`), kept live on resize/zoom and whenever content
 *        above it changes height. CSS owns floors and breakpoints, so SSR and
 *        no-JS fall back to the stylesheet value.
 */
import { useLayoutEffect, type RefObject } from "react";

/**
 * @brief Height that fills the viewport below a document offset.
 * @param top element's document top (px)
 * @param viewport window.innerHeight (px)
 * @param gap space to keep below the element (px)
 * @return whole px, never negative
 */
export function fillHeight(top: number, viewport: number, gap: number): number {
  return Math.max(0, Math.floor(viewport - top - gap));
}

/**
 * @brief Layout document top via offsetTop, so entrance transforms on
 *        ancestors don't skew the measurement (unlike getBoundingClientRect).
 * @param el element
 * @return px from the top of the document
 */
export function docTop(el: HTMLElement): number {
  let top = 0;
  for (let e: Element | null = el; e instanceof HTMLElement; ) {
    top += e.offsetTop;
    e = e.offsetParent;
  }
  return top;
}

/**
 * @brief Keep `name` on `ref` set to the viewport height below it.
 * @param ref element to size
 * @param name CSS custom property to set
 * @param gap px kept free below the element
 */
export function useFillHeight(
  ref: RefObject<HTMLElement | null>,
  name: string,
  gap = 0,
): void {
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () =>
      el.style.setProperty(
        name,
        `${fillHeight(docTop(el), window.innerHeight, gap)}px`,
      );
    update();
    window.addEventListener("resize", update);
    // Content above moving the element resizes one of these: the parent
    // (greeting, On-this-day), <main> (flex-1, shrinks/grows as Shell banners
    // come and go) or <body> (overflow). Same value again is a no-op: no loop.
    const ro =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(update);
    for (const t of [el.parentElement, el.closest("main"), document.body])
      if (t) ro?.observe(t);
    return () => {
      window.removeEventListener("resize", update);
      ro?.disconnect();
    };
  }, [ref, name, gap]);
}
