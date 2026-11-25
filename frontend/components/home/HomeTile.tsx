"use client";
/**
 * @file components/home/HomeTile.tsx
 * @brief Glass bento tile: panel with header link at md+, accordion on phone.
 */
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { animate, useReducedMotion } from "framer-motion";
import { collapseTransition } from "@/components/ui/motion";
import { ChevronDown, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TileId } from "@/hooks/useHomeAccordion";

/** @brief Props every tile slot receives from the home page. */
export interface TileSlotProps {
  open: boolean;
  onToggle: (id: TileId) => void;
}

export interface HomeTileProps extends TileSlotProps {
  id: TileId;
  title: string;
  icon: LucideIcon;
  href: string;
  linkLabel: string;
  summary?: string;
  count?: number;
  hot?: boolean;
  children: React.ReactNode;
  className?: string;
}

/**
 * @brief Tile shell. Body is always shown at md+, accordion below md.
 * @param props see HomeTileProps
 * @return section element
 */
export function HomeTile({
  id,
  title,
  icon: Icon,
  href,
  linkLabel,
  summary,
  count = 0,
  hot = false,
  open,
  onToggle,
  children,
  className,
}: HomeTileProps) {
  const bodyId = `tile-body-${id}`;
  const reduced = useReducedMotion();
  const bodyRef = React.useRef<HTMLDivElement>(null);
  const sectionRef = React.useRef<HTMLElement>(null);
  const wasOpen = React.useRef(open);
  const leaving = React.useRef(false);
  const router = useRouter();

  // Phone accordion: animate height on open only. CSS owns the rest state, so
  // desktop and no-JS content is never hidden; inline styles are cleared after.
  React.useLayoutEffect(() => {
    const was = wasOpen.current;
    wasOpen.current = open;
    const el = bodyRef.current;
    if (!open || was || !el || reduced) return;
    if (!window.matchMedia("(max-width: 767px)").matches) return;
    el.style.overflow = "hidden";
    const clear = () => {
      el.style.overflow = "";
      el.style.height = "";
    };
    animate(el, { height: [0, el.scrollHeight] }, collapseTransition).then(
      clear,
      clear,
    );
  }, [open, reduced]);

  const onLinkClick = async (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (
      reduced ||
      e.defaultPrevented ||
      e.button !== 0 ||
      e.metaKey ||
      e.ctrlKey ||
      e.shiftKey ||
      e.altKey
    )
      return;
    e.preventDefault();
    const el = sectionRef.current;
    if (!el || leaving.current) return;
    leaving.current = true;
    try {
      await animate(el, { scale: 1.02, opacity: 0.6 }, { duration: 0.15 });
    } finally {
      router.push(href);
      leaving.current = false;
      // Never leave the tile faded if navigation is slow.
      animate(el, { scale: 1, opacity: 1 }, { duration: 0.2 });
    }
  };
  return (
    <section
      ref={sectionRef}
      data-tile={id}
      className={cn(
        "glass glass-lift flex min-h-0 flex-col rounded-[26px] md:rounded-[32px]",
        className,
      )}
    >
      <button
        type="button"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => onToggle(id)}
        className="grid w-full grid-cols-[auto_1fr_auto_auto] items-center gap-3 rounded-[26px] px-4 py-3.5 text-left md:hidden"
      >
        <Icon className="h-5 w-5" aria-hidden />
        <span className="min-w-0">
          <span className="block font-medium">{title}</span>
          {summary ? (
            <span className="block truncate text-sm text-[var(--nx-muted)]">
              {summary}
            </span>
          ) : null}
        </span>
        {count > 0 ? (
          <span
            aria-label={`${count} ${hot ? "need you" : "new"}`}
            className={cn(
              "rounded-full px-2 py-0.5 text-xs font-medium",
              hot
                ? "bg-[var(--nx-red)] text-white"
                : "bg-surface-strong text-bg",
            )}
          >
            {count}
          </span>
        ) : (
          <span />
        )}
        <ChevronDown
          aria-hidden
          className={cn("h-4 w-4 transition-transform", open && "rotate-180")}
        />
      </button>
      <header className="hidden items-center justify-between px-5 pt-4 md:flex">
        <h2 className="flex items-center gap-2 text-lg font-medium">
          <Icon className="h-5 w-5" aria-hidden />
          {title}
        </h2>
        <Link
          href={href}
          onClick={onLinkClick}
          className="text-sm text-[var(--nx-muted)] hover:underline"
        >
          {linkLabel}
        </Link>
      </header>
      <div
        ref={bodyRef}
        id={bodyId}
        className={cn(
          "min-h-0 flex-1 flex-col px-3 pb-3 md:overflow-y-auto md:overscroll-contain md:px-4 md:pb-4",
          open ? "flex" : "hidden md:flex",
        )}
      >
        {children}
      </div>
    </section>
  );
}
