/**
 * @file components/layout/PageTransition.tsx
 * @brief Crossfade wrapper keyed on pathname; skipped under reduced motion.
 */
"use client";
import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { pageVariants } from "@/components/ui/motion";

/**
 * @brief Fade children in/out on route change (opacity only, no layout shift).
 * @param children Page content.
 */
export function PageTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const reduced = useReducedMotion();

  if (reduced) return <div data-pathname={pathname}>{children}</div>;

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={pathname}
        data-pathname={pathname}
        variants={pageVariants}
        initial="initial"
        animate="animate"
        exit="exit"
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
