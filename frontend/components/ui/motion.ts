/**
 * @file components/ui/motion.ts
 * @brief Motion primitives. Variants for page/modal/drawer/list-stagger.
 *        Spring/ease config inlined; reduced-motion respected via CSS.
 */
import { useReducedMotion } from "framer-motion";
import type { Variants, Transition } from "framer-motion";

export const spring: Transition = {
  type: "spring",
  stiffness: 200,
  damping: 24,
};
export const fast: Transition = { duration: 0.18, ease: [0.4, 0, 0.2, 1] };
export const page: Transition = { duration: 0.24, ease: [0.4, 0, 0.2, 1] };

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

export const drawerVariants = (
  side: "left" | "right" | "bottom" = "right",
): Variants => {
  const off = side === "left" ? "-100%" : side === "right" ? "100%" : "0";
  const offY = side === "bottom" ? "100%" : "0";
  return {
    hidden: { x: side === "bottom" ? 0 : off, y: offY, opacity: 1 },
    show: { x: 0, y: 0, transition: spring },
    exit: { x: side === "bottom" ? 0 : off, y: offY, transition: fast },
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
  animate: { opacity: 1, transition: { duration: 0.15, ease: "easeOut" } },
  exit: { opacity: 0, transition: { duration: 0.1 } },
};

/** Transition token for collapse/expand height animations. */
export const collapseTransition: import("framer-motion").Transition = fast;

export const tabPanelVariants: Variants = {
  initial: { opacity: 0, y: 4 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.18, ease: "easeOut" },
  },
  exit: { opacity: 0, y: -4, transition: { duration: 0.12 } },
};

/** Reaction click feedback: 1 -> 1.2 -> 1, 200ms spring. */
export const scalePress: Variants = {
  rest: { scale: 1 },
  pressed: {
    scale: [1, 1.2, 1],
    transition: { type: "spring", stiffness: 300, damping: 15, duration: 0.2 },
  },
};

/** New message slide-in. */
export const slideUp: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.2, ease: "easeOut" } },
  exit: { opacity: 0, transition: { duration: 0.15 } },
};

/** Opacity-only mount/exit (skeleton to content). */
export const fadeInOut: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.18, ease: "easeOut" } },
  exit: { opacity: 0, transition: { duration: 0.12 } },
};

/**
 * @brief Motion props for a variants set, or `{}` under prefers-reduced-motion.
 * @param variants variants using initial/animate/exit keys
 * @return props to spread on a motion element
 */
export function useMotionProps(variants: Variants) {
  const reduced = useReducedMotion();
  if (reduced) return {};
  return {
    variants,
    initial: "initial",
    animate: "animate",
    exit: "exit",
  } as const;
}
