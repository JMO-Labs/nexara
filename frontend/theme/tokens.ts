/**
 * @file theme/tokens.ts
 * @brief Warm Editorial design tokens. Single source of truth for colors,
 *        radii, elevation, motion. Joy theme + globals.css both consume these.
 */

export const colors = {
  ink: "#2B2A28",
  paper: "#F5EFE6",
  paperDark: "#1A1816",
  terracotta: "#C44536",
  terracottaSoft: "#D9695B",
  terracottaDeep: "#9A3528",
  teal: "#1F4E5F",
  tealSoft: "#3A6E80",
  ochre: "#D9A441",
  sage: "#7A8B6F",
  rose: "#A8485A",
  fog: "#E8DFD3",
  fogDeep: "#D4C9B9",
  fogDark: "#2B2825",
} as const;

export const radius = {
  sm: "8px",
  md: "16px",
  lg: "24px",
  xl: "32px",
} as const;

export const elevation = {
  xs: "0 1px 2px rgba(43, 42, 40, 0.06)",
  sm: "0 2px 8px rgba(43, 42, 40, 0.08)",
  md: "0 8px 24px rgba(43, 42, 40, 0.10)",
  lg: "0 20px 60px rgba(43, 42, 40, 0.14)",
} as const;

export const motion = {
  spring: { type: "spring", stiffness: 200, damping: 24 } as const,
  fast: { duration: 0.18, ease: [0.4, 0, 0.2, 1] } as const,
  page: { duration: 0.24, ease: [0.4, 0, 0.2, 1] } as const,
} as const;

export const fontStacks = {
  display: '"Fraunces", "Iowan Old Style", Georgia, serif',
  body: '"Geist", system-ui, -apple-system, sans-serif',
  mono: '"Geist Mono", ui-monospace, "SF Mono", Menlo, monospace',
} as const;
