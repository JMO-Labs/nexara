/**
 * @file components/layout/PageMasthead.tsx
 * @brief Editorial page header: atmospheric backdrop, oversized display
 *        title, hairline rule + uppercase metric line, optional right slot.
 */
import * as React from "react";
import { cn } from "@/lib/utils";

export interface PageMastheadProps {
  title: string;
  /** Small uppercase line to the right of the rule (e.g. "12 events this month"). */
  meta?: string;
  /** Optional slot rendered at right (button, action). */
  right?: React.ReactNode;
  /** Title scale; default "lg" matches galleries page. */
  size?: "md" | "lg";
}

const TITLE_SIZES = {
  md: "text-[12vw] sm:text-[64px] md:text-[92px] lg:text-[116px]",
  lg: "text-[14vw] sm:text-[88px] md:text-[120px] lg:text-[156px]",
} as const;

/**
 * @brief Page masthead.
 * @param props title, optional meta line, right slot and size
 * @return header element
 */
export function PageMasthead({
  title,
  meta,
  right,
  size = "lg",
}: PageMastheadProps) {
  return (
    <div className="relative mb-4 md:mb-6">
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-x-10 top-[-40px] bottom-0 z-0 bg-[radial-gradient(ellipse_1100px_480px_at_18%_-10%,color-mix(in_srgb,var(--color-sun)_18%,transparent)_0%,transparent_65%),radial-gradient(ellipse_800px_360px_at_95%_8%,color-mix(in_srgb,var(--color-accent)_10%,transparent)_0%,transparent_70%)]"
      />
      <div className="relative z-10 pt-6 pb-4 md:pt-10 md:pb-6">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <h1
              className={cn(
                "text-ink leading-[0.88] font-normal tracking-[-0.04em]",
                TITLE_SIZES[size],
              )}
            >
              {title}
            </h1>
            {meta && (
              <div className="mt-4 flex items-center gap-3">
                <span className="h-px w-14 bg-current opacity-35" />
                <span className="text-muted font-mono text-[11px] tracking-[0.18em] uppercase">
                  {meta}
                </span>
              </div>
            )}
          </div>
          {right && <div className="self-start md:self-auto">{right}</div>}
        </div>
      </div>
    </div>
  );
}

export default PageMasthead;
