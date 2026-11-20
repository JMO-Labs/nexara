/**
 * @file patterns.ts
 * @brief Home background pattern names and (Task 7) their SVG mask generators.
 */

/** @brief Pattern names accepted by settings and branding (must match backend regex). */
export const PATTERNS = ["none", "dots", "topo", "contour", "waves", "grain"] as const;

/** @brief One of {@link PATTERNS}. */
export type HomePattern = (typeof PATTERNS)[number];
