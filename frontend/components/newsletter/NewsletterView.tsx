"use client";
/**
 * @file components/newsletter/NewsletterView.tsx
 * @brief Printable newsletter: masthead, top posts, photos, birthdays,
 *        remembrances, recipes, opened capsules and events. Screen chrome
 *        (print button, month switcher, admin bar) is hidden when printing.
 */
import Link from "next/link";
import { ChevronLeft, ChevronRight, Printer } from "lucide-react";
import "@/app/print.css";
import { Button } from "@/components/ui";
import { mediaThumbUrl } from "@/lib/api/media";
import type { Newsletter, NewsPerson } from "@/lib/api/newsletter";
import { NewsletterAdminBar } from "./NewsletterAdminBar";

const CARD = "nx-news-card glass rounded-2xl p-4";

/** @param month YYYY-MM @param delta months to add @return shifted YYYY-MM */
export function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + delta, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

/** @return "November 2026" for a YYYY-MM string */
export function monthTitle(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

const day = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-6">
      <h2 className="mb-2 text-xl font-medium text-ink">{title}</h2>
      {children}
    </section>
  );
}

function People({ items }: { items: NewsPerson[] }) {
  return (
    <ul className="m-0 grid list-none gap-2 p-0 sm:grid-cols-2">
      {items.map((p, i) => (
        <li key={`${p.name}-${p.date}-${i}`} className={CARD}>
          <Link href={p.link} className="font-medium text-ink">
            {p.name}
          </Link>
          <span className="block text-sm text-muted">{day(p.date)}</span>
        </li>
      ))}
    </ul>
  );
}

/**
 * @param props newsletter data, previous/next availability, admin flag
 * @return the newsletter sheet
 */
export function NewsletterView({
  data,
  admin,
  canNext,
  canPrev,
}: {
  data: Newsletter;
  admin: boolean;
  canNext: boolean;
  canPrev: boolean;
}) {
  const m = data.month;
  const empty =
    !data.top_posts.length &&
    !data.photos.length &&
    !data.birthdays.length &&
    !data.remembrances.length &&
    !data.new_recipes.length &&
    !data.opened_capsules.length &&
    !data.events.length;
  return (
    <div className="nx-news mx-auto w-full max-w-[900px] pb-10">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 print:hidden">
        <nav aria-label="Month" className="flex items-center gap-2">
          {canPrev ? (
            <Button asChild variant="secondary" size="sm">
              <Link
                href={`/app/newsletter/${shiftMonth(m, -1)}`}
                aria-label="Previous month"
              >
                <ChevronLeft aria-hidden className="size-4" />
                {monthTitle(shiftMonth(m, -1))}
              </Link>
            </Button>
          ) : null}
          {canNext ? (
            <Button asChild variant="secondary" size="sm">
              <Link
                href={`/app/newsletter/${shiftMonth(m, 1)}`}
                aria-label="Next month"
              >
                {monthTitle(shiftMonth(m, 1))}
                <ChevronRight aria-hidden className="size-4" />
              </Link>
            </Button>
          ) : null}
        </nav>
        <Button onClick={() => window.print()}>
          <Printer aria-hidden className="size-4" />
          Print or save as PDF
        </Button>
      </div>
      {admin && (
        <NewsletterAdminBar
          month={m}
          posts={data.top_posts}
          hidden={data.hidden_posts}
        />
      )}
      <header className="nx-news-masthead mb-2 grid gap-1 border-b-2 border-ink pb-3 sm:grid-cols-2">
        <h1 className="text-[32px] leading-tight font-medium text-ink md:text-[40px]">
          {data.community_name} news
        </h1>
        <p className="text-lg text-muted sm:text-right">{monthTitle(m)}</p>
      </header>
      {empty && (
        <p className="mt-6 text-muted">Nothing to share from this month yet.</p>
      )}
      {data.top_posts.length > 0 && (
        <Section title="Top moments">
          <ul className="m-0 grid list-none gap-3 p-0">
            {data.top_posts.map((p) => (
              <li key={p.id} className={CARD}>
                {p.media_ids[0] && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={mediaThumbUrl(p.media_ids[0])}
                    alt=""
                    className="nx-news-photo mb-2 rounded-xl"
                  />
                )}
                <p className="m-0 text-ink">{p.excerpt}</p>
                <p className="m-0 mt-1 text-sm text-muted">
                  {p.author_name}, {p.reactions} reactions, {p.comments}{" "}
                  comments
                </p>
              </li>
            ))}
          </ul>
        </Section>
      )}
      {data.photos.length > 0 && (
        <Section title="Photos">
          <ul className="m-0 flex list-none flex-wrap gap-3 p-0">
            {data.photos.map((p) => (
              <li key={p.media_id} className="nx-news-card">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={mediaThumbUrl(p.media_id)}
                  alt={p.alt ?? "Photo from this month"}
                  className="nx-news-photo rounded-xl"
                />
              </li>
            ))}
          </ul>
        </Section>
      )}
      {data.birthdays.length > 0 && (
        <Section title="Birthdays">
          <People items={data.birthdays} />
        </Section>
      )}
      {data.remembrances.length > 0 && (
        <Section title="Remembering">
          <People items={data.remembrances} />
        </Section>
      )}
      {data.events.length > 0 && (
        <Section title="Events">
          <ul className="m-0 grid list-none gap-2 p-0">
            {data.events.map((e) => (
              <li key={e.id} className={CARD}>
                <span className="font-medium text-ink">{e.title}</span>
                <span className="block text-sm text-muted">
                  {day(e.date)}
                  {e.place ? `, ${e.place}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}
      {data.new_recipes.length > 0 && (
        <Section title="New recipes">
          <ul className="m-0 grid list-none gap-2 p-0 sm:grid-cols-2">
            {data.new_recipes.map((r) => (
              <li key={r.id} className={CARD}>
                <span className="font-medium text-ink">{r.title}</span>
                <span className="block text-sm text-muted">
                  by {r.author_name}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}
      {data.opened_capsules.length > 0 && (
        <Section title="Time capsules opened">
          <ul className="m-0 grid list-none gap-2 p-0 sm:grid-cols-2">
            {data.opened_capsules.map((c) => (
              <li key={c.id} className={CARD}>
                <span className="font-medium text-ink">{c.title}</span>
                <span className="block text-sm text-muted">
                  from {c.author_name}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  );
}
