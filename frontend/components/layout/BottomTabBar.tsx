"use client";
/**
 * @file components/layout/BottomTabBar.tsx
 * @brief Pinned glass phone tab bar: Home, Chat, Create, Calendar, Photos.
 */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useChatRealtime } from "@/hooks/useChat";
import { useSimpleMode } from "@/stores/simpleMode";
import { SIMPLE_NAV, TAB_NAV, isItemActive, type NavItem } from "./navItems";
import { CreateMenu } from "./CreateMenu";

/** Bottom padding Shell applies so content clears the bar. */
export const TAB_BAR_CLEARANCE =
  "pb-[calc(84px+env(safe-area-inset-bottom))] md:pb-0";

const TAB =
  "relative flex flex-1 flex-col items-center justify-center gap-0.5 rounded-2xl py-1 text-xs";

/**
 * @brief Phone bottom tab bar.
 * @return nav element
 */
export function BottomTabBar() {
  const pathname = usePathname();
  const reduced = useReducedMotion();
  const { unread } = useChatRealtime();
  const simple = useSimpleMode((s) => s.on);
  const tabs = simple ? SIMPLE_NAV : TAB_NAV;
  const total = Object.values(unread).reduce((a, b) => a + b, 0);

  const item = (nav: NavItem) => {
    const { label, href, Icon } = nav;
    const active = isItemActive(pathname, nav);
    return (
      <Link
        key={href}
        href={href}
        aria-current={active ? "page" : undefined}
        className={cn(TAB, active ? "text-bg" : "text-ink")}
      >
        {active && (
          <motion.span
            layoutId={reduced ? undefined : "tabbar-pill"}
            transition={{ type: "spring", stiffness: 500, damping: 40 }}
            className="bg-ink absolute inset-0 rounded-2xl"
            aria-hidden
          />
        )}
        <Icon aria-hidden className="relative size-5" />
        <span className="relative">{label}</span>
        {href === "/app/chat" && total > 0 && (
          <span className="bg-red text-bg absolute top-0 right-3 z-10 grid min-w-4 place-items-center rounded-full px-1 text-[10px] leading-4">
            {total}
          </span>
        )}
      </Link>
    );
  };

  return (
    <nav
      aria-label="Primary"
      className="glass fixed inset-x-0 bottom-0 z-40 mx-3 mb-[calc(.75rem+env(safe-area-inset-bottom))] flex h-[60px] items-center rounded-3xl p-1 md:hidden"
    >
      {tabs.slice(0, 2).map(item)}
      <CreateMenu compact className="mx-1 shrink-0" />
      {tabs.slice(2).map(item)}
    </nav>
  );
}
