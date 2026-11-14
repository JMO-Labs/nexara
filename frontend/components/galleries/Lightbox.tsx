"use client";
/**
 * @file components/galleries/Lightbox.tsx
 * @brief Full-screen modal viewer for gallery items: focus trap, arrows, Esc.
 */
import * as React from "react";
import { X, ChevronLeft, ChevronRight } from "lucide-react";
import { IconButton } from "@/components/ui";
import { API_BASE } from "@/lib/auth/session";
import type { GalleryItem } from "@/lib/api/galleries";

export interface LightboxProps {
  items: GalleryItem[];
  index: number;
  onClose: () => void;
  onIndexChange: (i: number) => void;
}

/**
 * @brief Modal image viewer.
 * @param items gallery items
 * @param index current item index
 * @param onClose close handler (Esc, backdrop, close button)
 * @param onIndexChange navigation handler
 * @return dialog or null when no item
 */
export function Lightbox({
  items,
  index,
  onClose,
  onIndexChange,
}: LightboxProps) {
  const item = items[index];
  const ref = React.useRef<HTMLDivElement>(null);
  // Track which src finished (load or error) so a new src starts hidden
  // in the same render, with no flash of the next image at full opacity.
  const [settledSrc, setSettledSrc] = React.useState<string | null>(null);

  const next = React.useCallback(() => {
    if (index < items.length - 1) onIndexChange(index + 1);
  }, [index, items.length, onIndexChange]);
  const prev = React.useCallback(() => {
    if (index > 0) onIndexChange(index - 1);
  }, [index, onIndexChange]);

  // Focus the dialog on open and restore focus on close.
  React.useEffect(() => {
    const prevFocus = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    return () => prevFocus?.focus?.();
  }, []);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopImmediatePropagation();
        onClose();
      } else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
      else if (e.key === "Tab" && ref.current) {
        const f = Array.from(
          ref.current.querySelectorAll<HTMLElement>("button:not([disabled])"),
        );
        if (f.length === 0) {
          e.preventDefault();
          return;
        }
        const first = f[0];
        const last = f[f.length - 1];
        const active = document.activeElement;
        if (e.shiftKey && (active === first || active === ref.current)) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && active === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [onClose, next, prev]);

  if (!item) return null;
  const src = `${API_BASE}/api/v1/media/${item.media_id}/file`;
  const loaded = settledSrc === src;
  const label = item.caption || `Image ${index + 1} of ${items.length}`;

  return (
    <div
      ref={ref}
      tabIndex={-1}
      role="dialog"
      aria-modal="true"
      aria-label="Lightbox viewer"
      onClick={onClose}
      className="fixed inset-0 z-[1500] flex flex-col bg-black/85 outline-none"
    >
      <div
        className="flex items-center justify-between p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <span className="text-sm text-white">
          {index + 1} / {items.length}
        </span>
        <IconButton
          variant="ghost"
          aria-label="Close"
          tooltip="Close"
          shortcut="Esc"
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
        >
          <X className="size-6 text-white" aria-hidden="true" />
        </IconButton>
      </div>
      <div
        className="relative flex min-h-0 flex-1 items-center justify-center"
        onClick={(e) => e.stopPropagation()}
      >
        <IconButton
          variant="ghost"
          aria-label="Previous"
          tooltip="Previous"
          shortcut="←"
          onClick={prev}
          disabled={index === 0}
          className="absolute left-2 z-10 bg-black/40 md:left-4"
        >
          <ChevronLeft className="size-7 text-white" aria-hidden="true" />
        </IconButton>
        {/* eslint-disable-next-line @next/next/no-img-element -- user/external URL, unknown host for next/image */}
        <img
          src={src}
          alt={label}
          onLoad={() => setSettledSrc(src)}
          onError={() => setSettledSrc(src)}
          className={`max-h-[80vh] max-w-[90vw] object-contain transition-opacity duration-300 ${loaded ? "opacity-100" : "opacity-0"}`}
        />
        <IconButton
          variant="ghost"
          aria-label="Next"
          tooltip="Next"
          shortcut="→"
          onClick={next}
          disabled={index >= items.length - 1}
          className="absolute right-2 z-10 bg-black/40 md:right-4"
        >
          <ChevronRight className="size-7 text-white" aria-hidden="true" />
        </IconButton>
      </div>
      {item.caption && (
        <p
          className="p-4 text-center text-sm text-white"
          onClick={(e) => e.stopPropagation()}
        >
          {item.caption}
        </p>
      )}
    </div>
  );
}

export default Lightbox;
