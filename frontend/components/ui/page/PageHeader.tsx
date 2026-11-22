/**
 * @file components/ui/page/PageHeader.tsx
 * @brief Page title row with optional description, actions and back link.
 */
import * as React from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";

export interface PageHeaderProps {
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  back?: { href: string; label: string };
}

/**
 * @brief Page header.
 * @param props see PageHeaderProps
 * @return header element
 */
export function PageHeader({
  title,
  description,
  actions,
  back,
}: PageHeaderProps) {
  return (
    <header className="mb-4 flex flex-wrap items-end justify-between gap-3 md:mb-[18px]">
      <div className="min-w-0">
        {back && (
          <Link
            href={back.href}
            className="mb-1 inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
          >
            <ChevronLeft className="size-4" aria-hidden="true" />
            {back.label}
          </Link>
        )}
        <h1 className="text-[32px] leading-tight font-medium tracking-[-0.02em] text-ink md:text-[40px]">
          {title}
        </h1>
        {description && (
          <div className="mt-1 text-[15px] text-muted">{description}</div>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}
