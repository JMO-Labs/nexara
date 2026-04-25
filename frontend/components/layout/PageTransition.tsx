'use client';
/**
 * @file components/layout/PageTransition.tsx
 * @brief Page-level motion wrapper. Wraps children to fade them in/out on
 *        route change. Key by pathname to reset on navigation.
 */
import { AnimatePresence, motion } from 'framer-motion';
import { usePathname } from 'next/navigation';
import { pageVariants } from '@/components/ui/motion';
import type { ReactNode } from 'react';

export function PageTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={pathname}
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

export default PageTransition;
