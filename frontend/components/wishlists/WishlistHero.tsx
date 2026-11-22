"use client";
/**
 * @file components/wishlists/WishlistHero.tsx
 * @brief Wishlist hero: occasion disc and glow, title, who it's for,
 *        event countdown and buy-by date, spend guidance, registries, and
 *        a planning bar (event budget) or the giver's own spend.
 */
import { CalendarClock, PackageCheck, ShoppingBag, Wallet } from "lucide-react";
import { OCCASIONS, occasionName } from "@/lib/occasions";
import { formatMoney } from "@/lib/money";
import { isHttpUrl } from "@/lib/profile";
import type { WishlistDetail } from "@/lib/api/wishlists";
import { countdown, dayLabel, daysUntil, recipientsText } from "./wishlistText";

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="glass-item inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm">
      {children}
    </span>
  );
}

/**
 * @brief Hero section.
 * @param w wishlist
 * @param actions owner buttons (edit, delete)
 * @return section
 */
export function WishlistHero({
  w,
  actions,
}: {
  w: WishlistDetail;
  actions?: React.ReactNode;
}) {
  const { Icon, tint } = OCCASIONS[w.occasion];
  const money = (c: number) => formatMoney(c, w.currency);
  const spend =
    w.budget_min_cents != null && w.budget_max_cents != null
      ? `${money(w.budget_min_cents)} to ${money(w.budget_max_cents)}`
      : w.budget_max_cents != null
        ? `Up to ${money(w.budget_max_cents)}`
        : w.budget_min_cents != null
          ? `From ${money(w.budget_min_cents)}`
          : null;
  const budgetPct =
    w.planned_cents != null && w.event_budget_cents
      ? Math.round((w.planned_cents / w.event_budget_cents) * 100)
      : null;
  const dueSoon = w.due_by ? daysUntil(w.due_by) : null;
  return (
    <section className="glass relative overflow-hidden rounded-[32px] p-6 sm:p-8">
      <span
        aria-hidden
        className="pointer-events-none absolute -top-24 -right-16 size-72 rounded-full opacity-30 blur-3xl"
        style={{ background: tint }}
      />
      <div className="relative flex flex-col gap-5 sm:flex-row sm:items-start">
        <span
          aria-hidden
          className="grid size-20 shrink-0 place-items-center rounded-full text-white shadow-[0_14px_30px_-12px_rgba(0,0,0,0.5)]"
          style={{ background: tint }}
        >
          <Icon className="size-9" />
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <p className="text-sm text-muted">
            {occasionName(w.occasion, w.occasion_label)}
          </p>
          <h1 className="text-3xl leading-tight font-semibold tracking-tight sm:text-4xl">
            {w.title}
          </h1>
          <p className="text-base">
            For {recipientsText(w.recipients) || w.owner_name}
            <span className="text-muted">
              {" "}
              · made by {w.is_owner ? "you" : w.owner_name}
            </span>
          </p>
          <div className="flex flex-wrap gap-2">
            {w.event_date && (
              <Chip>
                <CalendarClock className="size-4" aria-hidden />
                {dayLabel(w.event_date)},{" "}
                {countdown(w.event_date).toLowerCase()}
              </Chip>
            )}
            {w.due_by && (
              <Chip>
                <PackageCheck
                  className={
                    dueSoon != null && dueSoon <= 3
                      ? "size-4 text-[var(--nx-red)]"
                      : "size-4"
                  }
                  aria-hidden
                />
                Buy by {dayLabel(w.due_by)}
              </Chip>
            )}
            {spend && (
              <Chip>
                <Wallet className="size-4" aria-hidden /> Suggested {spend}
              </Chip>
            )}
            {w.giver_cap_cents != null && (
              <Chip>Limit {money(w.giver_cap_cents)} per person</Chip>
            )}
          </div>
          {w.note && (
            <p className="max-w-[65ch] text-base whitespace-pre-line">
              {w.note}
            </p>
          )}
          {w.registry_links.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {w.registry_links
                .filter((r) => isHttpUrl(r.url))
                .map((r) => (
                  <a
                    key={r.url}
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex h-10 items-center gap-2 rounded-full bg-surface-strong px-4 text-sm font-medium text-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  >
                    <ShoppingBag className="size-4" aria-hidden /> {r.label}
                    <span className="sr-only">(opens in a new tab)</span>
                  </a>
                ))}
            </div>
          )}
          {budgetPct != null && (
            <div className="flex max-w-md flex-col gap-1">
              <span className="text-sm">
                Planned {money(w.planned_cents ?? 0)} of{" "}
                {money(w.event_budget_cents ?? 0)} budget
              </span>
              <span
                role="progressbar"
                aria-label="Event budget used"
                aria-valuenow={Math.min(budgetPct, 100)}
                aria-valuemin={0}
                aria-valuemax={100}
                className="block h-2 overflow-hidden rounded-full bg-[color-mix(in_srgb,var(--nx-ink)_10%,transparent)]"
              >
                <span
                  className="block h-full rounded-full"
                  style={{
                    width: `${Math.min(budgetPct, 100)}%`,
                    background:
                      budgetPct > 100 ? "var(--nx-red)" : "var(--nx-accent)",
                  }}
                />
              </span>
            </div>
          )}
          {w.sees_claims && w.my_total_cents > 0 && (
            <p className="text-sm text-muted">
              You&apos;re giving {money(w.my_total_cents)}
              {w.giver_cap_cents != null &&
                ` of your ${money(w.giver_cap_cents)} limit`}
              .
            </p>
          )}
          {!w.sees_claims && (
            <p className="text-sm text-muted">
              Gifts are a surprise: you won&apos;t see who is getting what.
            </p>
          )}
        </div>
        {actions && <div className="flex gap-1 sm:self-start">{actions}</div>}
      </div>
    </section>
  );
}
