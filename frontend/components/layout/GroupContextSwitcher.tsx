"use client";
/**
 * @file components/layout/GroupContextSwitcher.tsx
 * @brief Unobtrusive group context switcher in TopBar. Hidden if 0 groups.
 *        Shows active group name on /app/subgroups/[slug] routes.
 *        Shows "Groups ▾" for ≥2 groups otherwise.
 */
import * as React from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/shadcn/dropdown-menu";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { gradientFor, monogram } from "@/lib/groupVisuals";

/**
 * @brief Group switcher dropdown.
 * @return dropdown menu, or null when there is nothing to switch between
 */
export function GroupContextSwitcher() {
  const router = useRouter();
  const pathname = usePathname();
  const { data: groups = [] } = useSubgroupList();

  const activeSlug = pathname.match(/^\/app\/subgroups\/([^/?]+)/)?.[1];
  const activeGroup = activeSlug
    ? groups.find((g) => g.slug === activeSlug)
    : null;

  if (groups.length === 0) return null;
  if (groups.length === 1 && !activeGroup) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Switch group context"
        className="hover:bg-surface rounded-md px-2 py-1.5 text-sm"
      >
        {activeGroup ? `${activeGroup.name} ▾` : "Groups ▾"}
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        className="max-h-[400px] min-w-60 overflow-y-auto"
      >
        {groups.map((g) => (
          <DropdownMenuItem
            key={g.id}
            onSelect={() => router.push(`/app/subgroups/${g.slug}`)}
            className={g.parent_id ? "gap-3 pl-8" : "gap-3"}
          >
            <span
              aria-hidden
              className="flex size-8 items-center justify-center rounded-full text-xs font-semibold text-[#333]"
              style={{ background: gradientFor(g.slug).monogramBg }}
            >
              {monogram(g.name)}
            </span>
            <span className="flex-1 text-sm font-medium">{g.name}</span>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild className="justify-center">
          <Link href="/app/subgroups" className="text-xs opacity-70">
            All groups →
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
