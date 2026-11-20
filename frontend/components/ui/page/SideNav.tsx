/**
 * @file components/ui/page/SideNav.tsx
 * @brief Section nav: vertical glass list at md+, scrollable pills on phone.
 */
import * as React from "react";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SideNavProps {
  items: { id: string; label: string; href: string; icon?: LucideIcon }[];
  activeId: string;
  label: string;
}

/**
 * @brief Side navigation.
 * @param activeId id of the current item (ink pill)
 * @param label nav aria-label
 * @return nav element
 */
export function SideNav({ items, activeId, label }: SideNavProps) {
  return (
    <nav
      aria-label={label}
      className="glass flex gap-1 overflow-x-auto whitespace-nowrap rounded-full p-1 md:flex-col md:overflow-visible md:rounded-[28px] md:p-2"
    >
      {items.map((it) => {
        const active = it.id === activeId;
        const Icon = it.icon;
        return (
          <Link
            key={it.id}
            href={it.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-full px-3.5 py-2 text-sm transition-colors outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
              active
                ? "bg-surface-strong text-bg"
                : "text-ink hover:bg-white/30",
            )}
          >
            {Icon && <Icon className="size-4" aria-hidden="true" />}
            {it.label}
          </Link>
        );
      })}
    </nav>
  );
}
