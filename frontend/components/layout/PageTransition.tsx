"use client";
/**
 * @file components/layout/PageTransition.tsx
 * @brief Page-level fade on route change. Renders only the current page —
 *        no AnimatePresence stacking — to avoid layout shifts where the
 *        outgoing page would push the incoming one down inside the flex
 *        column.
 */
import { motion } from "framer-motion";
import { usePathname } from "next/navigation";
import { pageVariants } from "@/components/ui/motion";
import type { ReactNode } from "react";

export function PageTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <motion.div
      key={pathname}
      variants={pageVariants}
      initial="initial"
      animate="animate"
      style={{
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
      }}
    >
      {children}
    </motion.div>
  );
}

export default PageTransition;
