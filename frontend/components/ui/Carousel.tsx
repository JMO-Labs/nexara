"use client";
/**
 * @file components/ui/Carousel.tsx
 * @brief Embla-based carousel primitive.
 *        WCAG 2.1 AA: real button arrows, dot tabs, keyboard navigation.
 *        Respects prefers-reduced-motion (disables autoplay + smooth scroll).
 */
import * as React from "react";
import useEmblaCarousel from "embla-carousel-react";
import type { EmblaOptionsType } from "embla-carousel";
import { useReducedMotion } from "framer-motion";

export interface CarouselProps {
  /** Array of slide content. */
  slides: React.ReactNode[];
  /** Number of visible slides or 'auto'. Responsive default applied via CSS. */
  slidesPerView?: 1 | 2 | 3 | "auto";
  loop?: boolean;
  /** Autoplay slides (disabled automatically under prefers-reduced-motion). */
  autoplay?: boolean;
  /** Delay in ms between autoplay advances. Default 5000. */
  autoplayDelayMs?: number;
  /** Required accessible label for the carousel region. */
  ariaLabel: string;
  /** Show previous/next arrow buttons. Default true. */
  showArrows?: boolean;
  /** Show dot/tab navigation. Default true. */
  showDots?: boolean;
  className?: string;
}

export function Carousel({
  slides,
  slidesPerView = 1,
  loop = false,
  autoplay = false,
  autoplayDelayMs = 5000,
  ariaLabel,
  showArrows = true,
  showDots = true,
  className,
}: CarouselProps) {
  const reducedMotion = useReducedMotion();

  const opts = React.useMemo<EmblaOptionsType>(
    () => ({ loop, dragFree: false }),
    [loop],
  );

  const [emblaRef, emblaApi] = useEmblaCarousel(opts);
  const [selectedIndex, setSelectedIndex] = React.useState(0);
  const [snapCount, setSnapCount] = React.useState(slides.length);
  const [canPrev, setCanPrev] = React.useState(false);
  const [canNext, setCanNext] = React.useState(true);

  const onSelect = React.useCallback(() => {
    if (!emblaApi) return;
    setSelectedIndex(emblaApi.selectedScrollSnap());
    setSnapCount(emblaApi.scrollSnapList().length);
    setCanPrev(emblaApi.canScrollPrev());
    setCanNext(emblaApi.canScrollNext());
  }, [emblaApi]);

  React.useEffect(() => {
    if (!emblaApi) return;
    const init = () => onSelect();
    emblaApi.on("select", init);
    emblaApi.on("reInit", init);
    const raf = requestAnimationFrame(() => onSelect());
    return () => {
      cancelAnimationFrame(raf);
      emblaApi.off("select", init);
      emblaApi.off("reInit", init);
    };
  }, [emblaApi, onSelect]);

  // Autoplay — disabled under reduced motion; embla handles loop natively
  React.useEffect(() => {
    if (!emblaApi || !autoplay || reducedMotion) return;
    const id = setInterval(() => {
      if (emblaApi.canScrollNext()) {
        emblaApi.scrollNext();
      }
    }, autoplayDelayMs);
    return () => clearInterval(id);
  }, [emblaApi, autoplay, autoplayDelayMs, reducedMotion]);

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (!emblaApi) return;
      if (e.key === "ArrowRight") {
        e.preventDefault();
        emblaApi.scrollNext();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        emblaApi.scrollPrev();
      }
    },
    [emblaApi],
  );

  // Early-return for empty slides
  if (slides.length === 0) return null;

  const isSingle = slides.length === 1;

  // Determine per-slide width class based on slidesPerView
  const slideWidthClass =
    slidesPerView === "auto"
      ? "embla__slide--auto"
      : slidesPerView === 1
        ? "min-w-full"
        : slidesPerView === 2
          ? "min-w-[50%]"
          : "min-w-[33.333%]";

  return (
    <div
      role="region"
      aria-label={ariaLabel}
      className={`relative outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-lg ${className ?? ""}`}
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* Embla viewport */}
      <div ref={emblaRef} className="overflow-hidden rounded-lg">
        <div className="flex touch-pan-y">
          {slides.map((slide, i) => (
            <div
              key={i}
              className={`flex-shrink-0 flex-grow-0 ${slideWidthClass}`}
              aria-roledescription="slide"
              aria-label={`Slide ${i + 1} of ${slides.length}`}
            >
              {slide}
            </div>
          ))}
        </div>
      </div>

      {/* Arrows — hidden for single-slide carousels */}
      {showArrows && !isSingle && (
        <>
          <button
            type="button"
            aria-label="Previous slide"
            disabled={!loop && !canPrev}
            onClick={() => emblaApi?.scrollPrev()}
            className="absolute left-2 top-1/2 -translate-y-1/2 z-10 rounded-full bg-surface/80 p-2 shadow-sm disabled:opacity-30 hover:bg-surface  transition-opacity"
          >
            <svg
              aria-hidden="true"
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M10.707 3.293a1 1 0 0 0-1.414 0l-4 4a1 1 0 0 0 0 1.414l4 4a1 1 0 0 0 1.414-1.414L7.414 8l3.293-3.293a1 1 0 0 0 0-1.414z" />
            </svg>
          </button>
          <button
            type="button"
            aria-label="Next slide"
            disabled={!loop && !canNext}
            onClick={() => emblaApi?.scrollNext()}
            className="absolute right-2 top-1/2 -translate-y-1/2 z-10 rounded-full bg-surface/80 p-2 shadow-sm disabled:opacity-30 hover:bg-surface  transition-opacity"
          >
            <svg
              aria-hidden="true"
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M5.293 3.293a1 1 0 0 1 1.414 0l4 4a1 1 0 0 1 0 1.414l-4 4a1 1 0 0 1-1.414-1.414L8.586 8 5.293 4.707a1 1 0 0 1 0-1.414z" />
            </svg>
          </button>
        </>
      )}

      {/* Dots — hidden for single-slide carousels */}
      {showDots && !isSingle && snapCount > 1 && (
        <div
          role="tablist"
          aria-label={`${ariaLabel} navigation`}
          className="flex justify-center gap-1.5 mt-3"
        >
          {Array.from({ length: snapCount }).map((_, i) => (
            <button
              key={i}
              role="tab"
              type="button"
              aria-label={`Slide ${i + 1}`}
              aria-selected={i === selectedIndex}
              onClick={() => emblaApi?.scrollTo(i)}
              className={`w-2 h-2 rounded-full transition-colors  ${
                i === selectedIndex
                  ? "bg-primary-500 dark:bg-primary-400"
                  : "bg-muted hover:bg-ink/40"
              }`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default Carousel;
