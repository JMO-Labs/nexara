/**
 * @file components/ui/motion.ts
 * @brief Motion primitives. Variants for page/modal/drawer/list-stagger.
 *        Spring config from theme tokens; reduced-motion respected via CSS.
 */
import type { Variants, Transition } from 'framer-motion';
import { motion as tokens } from '@/theme/tokens';

export const spring: Transition = tokens.spring;
export const fast: Transition = tokens.fast;
export const page: Transition = tokens.page;

export const fadeSlide: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: page },
  exit: { opacity: 0, y: -4, transition: fast },
};

export const modalVariants: Variants = {
  hidden: { opacity: 0, scale: 0.96, y: 12 },
  show: { opacity: 1, scale: 1, y: 0, transition: spring },
  exit: { opacity: 0, scale: 0.98, y: 8, transition: fast },
};

export const drawerVariants = (side: 'left' | 'right' | 'bottom' = 'right'): Variants => {
  const off = side === 'left' ? '-100%' : side === 'right' ? '100%' : '0';
  const offY = side === 'bottom' ? '100%' : '0';
  return {
    hidden: { x: side === 'bottom' ? 0 : off, y: offY, opacity: 1 },
    show: { x: 0, y: 0, transition: spring },
    exit: { x: side === 'bottom' ? 0 : off, y: offY, transition: fast },
  };
};

export const listStagger: Variants = {
  show: { transition: { staggerChildren: 0.04, delayChildren: 0.04 } },
  exit: {},
};

export const listItem: Variants = {
  hidden: { opacity: 0, y: 6 },
  show: { opacity: 1, y: 0, transition: page },
  exit: { opacity: 0, transition: fast },
};

export const pressScale = {
  whileTap: { scale: 0.97 },
  whileHover: { scale: 1.01 },
  transition: spring,
};

export const pageVariants: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.15, ease: 'easeOut' } },
  exit: { opacity: 0, transition: { duration: 0.1 } },
};

export const tabPanelVariants: Variants = {
  initial: { opacity: 0, y: 4 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.18, ease: 'easeOut' } },
  exit: { opacity: 0, y: -4, transition: { duration: 0.12 } },
};
