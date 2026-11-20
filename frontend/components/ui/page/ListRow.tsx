/**
 * @file components/ui/page/ListRow.tsx
 * @brief Glass list item: link, button or static row.
 */
import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

export interface ListRowProps {
  children: React.ReactNode;
  href?: string;
  onClick?: () => void;
  selected?: boolean;
  className?: string;
  "data-testid"?: string;
}

/**
 * @brief List row.
 * @param href renders a next/link
 * @param onClick renders a button
 * @param selected adds ring and aria-current
 * @return a, button or div
 */
export function ListRow({
  children,
  href,
  onClick,
  selected,
  className,
  ...rest
}: ListRowProps) {
  const cls = cn(
    "glass-item flex w-full items-center gap-3 rounded-[22px] px-4 py-3 text-left text-ink",
    (href || onClick) &&
      "transition-colors hover:bg-white/30 outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
    selected && "ring-2 ring-ink",
    className,
  );
  const cur = selected ? { "aria-current": "true" as const } : {};
  if (href)
    return (
      <Link href={href} className={cls} {...cur} {...rest}>
        {children}
      </Link>
    );
  if (onClick)
    return (
      <button
        type="button"
        onClick={onClick}
        className={cls}
        {...cur}
        {...rest}
      >
        {children}
      </button>
    );
  return (
    <div className={cls} {...cur} {...rest}>
      {children}
    </div>
  );
}
