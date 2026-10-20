"use client";
/**
 * @file components/layout/BottomTabBar.tsx
 * @brief Floating phone tab bar: 4 primary destinations + More sheet.
 */
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Ellipsis } from "lucide-react";
import { cn } from "@/lib/utils";
import { PRIMARY_NAV, isNavActive } from "./navItems";
import { MoreSheet } from "./MoreSheet";

/** Bottom padding Shell applies so content clears the bar. */
export const TAB_BAR_CLEARANCE =
  "pb-[calc(84px+env(safe-area-inset-bottom))] md:pb-0";

const TAB =
  "flex flex-1 flex-col items-center justify-center gap-0.5 rounded-2xl py-1 text-xs";

/**
 * @brief Phone bottom tab bar.
 * @return nav element plus More sheet
 */
export function BottomTabBar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <>
      <nav
        aria-label="Primary"
        className="fixed inset-x-0 bottom-0 z-40 mx-3 mb-[calc(.75rem+env(safe-area-inset-bottom))] flex h-[60px] rounded-3xl bg-surface-strong text-muted shadow-lg md:hidden"
      >
        {PRIMARY_NAV.map(({ label, href, Icon }) => {
          const active = isNavActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(TAB, active && "text-accent")}
            >
              <Icon aria-hidden className="size-5" />
              <span>{label}</span>
            </Link>
          );
        })}
        <button
          type="button"
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => setOpen(true)}
          className={TAB}
        >
          <Ellipsis aria-hidden className="size-5" />
          <span>More</span>
        </button>
      </nav>
      <MoreSheet open={open} onClose={() => setOpen(false)} />
    </>
  );
}
