"use client";
/**
 * @file components/layout/TopNav.tsx
 * @brief Desktop glass pill nav with a gliding active pill that compacts on scroll.
 */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { TOP_NAV, isItemActive } from "./navItems";

const LINK =
  "relative inline-flex items-center rounded-full px-5 py-2.5 text-sm focus-visible:outline-accent focus-visible:outline-2 focus-visible:outline-offset-2";

/**
 * @brief Top pill navigation.
 * @return nav element
 */
export function TopNav() {
  const pathname = usePathname();
  const reduced = useReducedMotion();
  return (
    <motion.nav
      layout={!reduced}
      transition={{ type: "spring", stiffness: 500, damping: 40 }}
      aria-label="Main"
      className="glass flex items-center gap-0.5 rounded-full p-1"
    >
      {TOP_NAV.map((item) => {
        const { label, href } = item;
        const active = isItemActive(pathname, item);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn(LINK, active ? "text-bg" : "text-ink")}
          >
            {active && (
              <motion.span
                layoutId={reduced ? undefined : "topnav-pill"}
                transition={{ type: "spring", stiffness: 500, damping: 40 }}
                className="bg-ink absolute inset-0 -z-0 rounded-full"
                aria-hidden
              />
            )}
            <span className="relative">{label}</span>
          </Link>
        );
      })}
    </motion.nav>
  );
}
