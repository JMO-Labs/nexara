"use client";
/**
 * @file components/lists/pages/PageChrome.tsx
 * @brief Shared chrome for /app/lists routes: breadcrumbs, page header,
 *        loading skeleton and error card.
 */
import type { ReactNode } from "react";
import Link from "next/link";
import { AlertTriangle, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";

export interface Crumb {
  label: string;
  href?: string;
}

/**
 * @brief Breadcrumb trail; last crumb is the current page.
 * @param props crumbs, root first
 * @return nav
 */
export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb">
      <ol className="flex flex-wrap items-center gap-1 text-sm text-muted">
        {items.map((c, i) => (
          <li key={`${c.label}-${i}`} className="flex items-center gap-1">
            {i > 0 && <ChevronRight aria-hidden className="size-3.5" />}
            {c.href && i < items.length - 1 ? (
              <Link href={c.href} className="hover:underline">
                {c.label}
              </Link>
            ) : (
              <span aria-current="page">{c.label}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

/**
 * @brief Page header with breadcrumbs, title and optional actions.
 * @param props crumbs, title, actions; hideTitle keeps the h1 for screen
 *        readers only (when the body already shows the title visually)
 * @return header
 */
export function PageHeader({
  crumbs,
  title,
  actions,
  hideTitle,
}: {
  crumbs: Crumb[];
  title: string;
  actions?: ReactNode;
  hideTitle?: boolean;
}) {
  return (
    <header className="flex flex-col gap-2">
      <Breadcrumbs items={crumbs} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className={hideTitle ? "sr-only" : "text-3xl font-black"}>
          {title}
        </h1>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
    </header>
  );
}

/** @brief Skeleton placeholder for list pages. */
export function PageSkeleton() {
  return (
    <div
      data-testid="list-page-loading"
      role="status"
      aria-label="Loading"
      className="flex flex-col gap-4"
    >
      <Skeleton height={16} width={160} />
      <Skeleton height={36} width={240} />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={120} rounded="lg" />
        ))}
      </div>
    </div>
  );
}

/**
 * @brief Error card with optional retry.
 * @param props title, message, retry handler
 * @return alert card
 */
export function ErrorCard({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <Card role="alert" className="flex flex-col items-start gap-3 p-6">
      <div className="flex items-center gap-2">
        <AlertTriangle aria-hidden className="size-5 text-destructive" />
        <h2 className="text-lg font-semibold">{title}</h2>
      </div>
      <p className="text-sm text-muted">{message}</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          Try again
        </Button>
      )}
    </Card>
  );
}

export const LISTS_CRUMB: Crumb = { label: "Lists", href: "/app/lists" };
export const TEMPLATES_CRUMB: Crumb = {
  label: "Templates",
  href: "/app/lists/templates",
};
