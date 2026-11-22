"use client";
/**
 * @file components/lists/pages/ListNewView.tsx
 * @brief /app/lists/new: list builder. Step one picks what you're making
 *        (a list, a wishlist, or a template); ?type= jumps straight in.
 *        Cancel returns to /app/inbox?view=lists, or back to the group when
 *        opened with ?subgroup=<id>.
 */
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Gift,
  LayoutTemplate,
  ListChecks,
  type LucideIcon,
} from "lucide-react";
import { Panel } from "@/components/ui/page";
import { useCommunityId } from "@/hooks/useCommunityId";
import { WishlistWizard } from "@/components/wishlists/wizard/WishlistWizard";
import { ListCreateForm } from "../ListCreateForm";
import { LISTS_CRUMB, PageHeader } from "./PageChrome";

const KINDS: {
  type: string;
  title: string;
  text: string;
  Icon: LucideIcon;
  tint: string;
  href?: string;
}[] = [
  {
    type: "list",
    title: "List",
    text: "To-dos, chores, packing, sign-ups. Hand out items and see who did what.",
    Icon: ListChecks,
    tint: "var(--nx-accent)",
  },
  {
    type: "wishlist",
    title: "Wishlist",
    text: "Birthdays, showers, holidays, reunions. Gifts, cash funds and registries.",
    Icon: Gift,
    tint: "var(--nx-red)",
  },
  {
    type: "template",
    title: "From a template",
    text: "Start from a ready-made list and adjust it.",
    Icon: LayoutTemplate,
    tint: "#7A8A55",
    href: "/app/lists/templates",
  },
];

/** @brief New list page body. */
export function ListNewView() {
  const router = useRouter();
  const params = useSearchParams();
  const communityId = useCommunityId();
  const subgroupId = params.get("subgroup");
  const type = params.get("type");
  const back = () =>
    subgroupId ? router.back() : router.push("/app/inbox?view=lists");
  const pick = (t: string) => {
    const next = new URLSearchParams(params);
    next.set("type", t);
    router.replace(`/app/lists/new?${next}`);
  };
  const title =
    type === "wishlist"
      ? "New wishlist"
      : type === "list"
        ? "New list"
        : "What are you making?";

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-4">
      <PageHeader
        crumbs={[LISTS_CRUMB, { label: "New" }]}
        title={title}
        description={
          type === "wishlist"
            ? "Three quick steps: the occasion, who it's for, then dates and money."
            : "Lists keep everyone on the same page."
        }
      />
      {type === "wishlist" ? (
        <Panel>
          <WishlistWizard onCancel={() => router.replace("/app/lists/new")} />
        </Panel>
      ) : type === "list" ? (
        <Panel>
          <ListCreateForm
            communityId={communityId}
            subgroupId={subgroupId}
            onDone={back}
            onCancel={back}
          />
        </Panel>
      ) : (
        <ul className="grid gap-4 md:grid-cols-3" aria-label="Kinds of list">
          {KINDS.map(({ type: t, title: name, text, Icon, tint, href }) => {
            const body = (
              <>
                <span
                  aria-hidden
                  className="pointer-events-none absolute -top-12 -right-12 size-40 rounded-full opacity-25 blur-2xl"
                  style={{ background: tint }}
                />
                <span
                  aria-hidden
                  className="grid size-14 place-items-center rounded-full text-white shadow-[0_12px_24px_-10px_rgba(0,0,0,0.5)]"
                  style={{ background: tint }}
                >
                  <Icon className="size-6" />
                </span>
                <span className="text-xl font-semibold">{name}</span>
                <span className="text-sm text-muted">{text}</span>
              </>
            );
            const cls =
              "glass glass-lift relative flex h-full w-full flex-col items-start gap-3 overflow-hidden rounded-[28px] p-6 text-left outline-none focus-visible:outline-2 focus-visible:outline-accent";
            return (
              <li key={t}>
                {href ? (
                  <Link href={href} className={cls}>
                    {body}
                  </Link>
                ) : (
                  <button type="button" className={cls} onClick={() => pick(t)}>
                    {body}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
