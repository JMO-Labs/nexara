/**
 * @file components/layout/PageTransition.tsx
 * @brief Fade-in keyed on pathname; skipped under reduced motion.
 *
 * No exit animation on purpose: with App Router, AnimatePresence mode="wait"
 * renders the NEW page inside the exiting wrapper and then mounts it a second
 * time, wiping form input and doubling effects/fetches.
 */
"use client";
import { useRef, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { pageVariants } from "@/components/ui/motion";

/**
 * @brief Fade children in on route change (opacity only, no layout shift).
 * @param children Page content.
 */
export function PageTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const reduced = useReducedMotion();
  // Skip the fade on the first page of the session (as before).
  const first = useRef(pathname);

  if (reduced) return <div data-pathname={pathname}>{children}</div>;

  return (
    <motion.div
      key={pathname}
      data-pathname={pathname}
      variants={pageVariants}
      initial={pathname === first.current ? false : "initial"}
      animate="animate"
    >
      {children}
    </motion.div>
  );
}
