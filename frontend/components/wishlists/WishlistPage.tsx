"use client";
/**
 * @file components/wishlists/WishlistPage.tsx
 * @brief One wishlist. Owners add, edit and remove wishes and never see
 *        claims. Everyone else sees what is left and can say "I'll get this".
 */
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, ExternalLink, Gift, Pencil, Trash2 } from "lucide-react";
import { Button, EmptyState, IconButton, Skeleton } from "@/components/ui";
import { useMemberProfile } from "@/hooks/useMembers";
import { useWishlist, useWishlistActions } from "@/hooks/useWishlists";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { LEVEL_LABEL, isHttpUrl } from "@/lib/profile";
import {
  OCCASION_LABEL,
  type Wish,
  type WishlistDetail,
} from "@/lib/api/wishlists";
import { occasionDay } from "./WishlistCards";
import { WishForm } from "./WishForm";
import { WishlistEditor } from "./WishlistEditor";

function GiverActions({ w, item }: { w: WishlistDetail; item: Wish }) {
  const { claim, release } = useWishlistActions();
  const mine = item.mine ?? 0;
  const left = item.qty - (item.claimed ?? 0);
  const busy = claim.isPending || release.isPending;
  const take = (qty: number) =>
    claim.mutate({ id: w.id, itemId: item.id, qty });
  if (mine > 0)
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-[var(--nx-ok)]">
          You&apos;re getting {item.qty > 1 ? mine : "this"}
        </span>
        {left > 0 && (
          <Button
            size="sm"
            variant="ghost"
            disabled={busy}
            onClick={() => take(mine + 1)}
          >
            One more
          </Button>
        )}
        <Button
          size="sm"
          variant="ghost"
          disabled={busy}
          onClick={() => release.mutate({ id: w.id, itemId: item.id })}
        >
          Undo
        </Button>
      </div>
    );
  if (left <= 0)
    return <span className="text-sm text-muted">Someone has this</span>;
  return (
    <Button size="sm" disabled={busy} onClick={() => take(1)}>
      I&apos;ll get this
    </Button>
  );
}

function WishRow({ w, item }: { w: WishlistDetail; item: Wish }) {
  const { updateWish, deleteWish } = useWishlistActions();
  const confirm = useConfirmDialog((s) => s.confirm);
  const [editing, setEditing] = React.useState(false);
  if (editing)
    return (
      <li className="glass-item rounded-[20px] p-3">
        <WishForm
          wish={item}
          pending={updateWish.isPending}
          onCancel={() => setEditing(false)}
          onSave={(body) =>
            updateWish
              .mutateAsync({ id: w.id, itemId: item.id, body })
              .then(() => setEditing(false))
          }
        />
      </li>
    );
  const left = w.is_owner ? null : item.qty - (item.claimed ?? 0);
  return (
    <li className="glass-item flex flex-col gap-2 rounded-[20px] p-4 sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-baseline gap-x-2 font-medium">
          {item.url && isHttpUrl(item.url) ? (
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 underline-offset-2 hover:underline"
            >
              {item.name}
              <ExternalLink className="size-3.5" aria-hidden />
              <span className="sr-only">(opens in a new tab)</span>
            </a>
          ) : (
            item.name
          )}
          {item.price && (
            <span className="text-sm text-muted">{item.price}</span>
          )}
          {item.qty > 1 && (
            <span className="text-sm text-muted">
              {left !== null
                ? `${Math.max(left, 0)} of ${item.qty} left`
                : `× ${item.qty}`}
            </span>
          )}
        </p>
        {item.notes && <p className="text-sm text-muted">{item.notes}</p>}
      </div>
      {w.is_owner ? (
        <div className="flex gap-1">
          <IconButton
            variant="ghost"
            size="sm"
            aria-label={`Edit ${item.name}`}
            onClick={() => setEditing(true)}
          >
            <Pencil className="size-4" aria-hidden />
          </IconButton>
          <IconButton
            variant="ghost"
            size="sm"
            aria-label={`Remove ${item.name}`}
            onClick={async () => {
              if (
                await confirm({
                  title: `Remove ${item.name}?`,
                  message: "Anyone planning to give it will no longer see it.",
                  confirmLabel: "Remove",
                  tone: "danger",
                })
              )
                deleteWish.mutate({ id: w.id, itemId: item.id });
            }}
          >
            <Trash2 className="size-4" aria-hidden />
          </IconButton>
        </div>
      ) : (
        <GiverActions w={w} item={item} />
      )}
    </li>
  );
}

/**
 * @brief Wishlist detail page body.
 * @param id wishlist id
 * @return page
 */
export function WishlistPage({ id }: { id: string }) {
  const router = useRouter();
  const { data: w, isLoading, isError } = useWishlist(id);
  const owner = useMemberProfile(w && !w.household ? w.owner_id : "");
  const { addWish, remove } = useWishlistActions();
  const confirm = useConfirmDialog((s) => s.confirm);
  const [editing, setEditing] = React.useState(false);

  if (isLoading) return <Skeleton height={240} rounded="lg" />;
  if (isError || !w)
    return (
      <EmptyState
        icon={Gift}
        title="Wishlist not found"
        description="It was deleted or isn't shared with you."
      />
    );
  const forName = w.household?.name ?? owner.data?.display_name ?? "";
  const back = w.household
    ? { href: `/app/household/${w.household.id}`, label: w.household.name }
    : {
        href: `/app/members/${w.owner_id}?tab=wishlists`,
        label: forName || "Profile",
      };
  const when = occasionDay(w.occasion_date);

  return (
    <div className="mx-auto flex w-full max-w-[960px] flex-col gap-5 pb-8">
      <Link
        href={back.href}
        className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
      >
        <ChevronLeft className="size-4" aria-hidden /> {back.label}
      </Link>
      <section className="glass flex flex-col gap-3 rounded-[28px] p-6">
        <p className="flex flex-wrap items-center gap-2 text-sm text-muted">
          <Gift className="size-4 text-[var(--nx-red)]" aria-hidden />
          {OCCASION_LABEL[w.occasion]}
          {when && <span>{when}</span>}
          {forName && <span>For {forName}</span>}
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">{w.title}</h1>
        {w.note && <p className="max-w-[65ch] text-base">{w.note}</p>}
        {w.is_owner && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted">
              Seen by: {LEVEL_LABEL[w.visibility]}. You won&apos;t see who is
              getting what.
            </span>
            <div className="flex-1" />
            <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>
              <Pencil className="size-4" aria-hidden /> Edit
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={async () => {
                if (
                  await confirm({
                    title: `Delete ${w.title}?`,
                    message:
                      "The list and its wishes are removed for everyone.",
                    confirmLabel: "Delete",
                    tone: "danger",
                  })
                )
                  remove.mutate(w.id, {
                    onSuccess: () => router.push(back.href),
                  });
              }}
            >
              <Trash2 className="size-4" aria-hidden /> Delete
            </Button>
          </div>
        )}
      </section>

      {w.items.length === 0 ? (
        <EmptyState
          compact
          icon={Gift}
          title={w.is_owner ? "Add the first wish" : "Nothing on this list yet"}
        />
      ) : (
        <ul aria-label="Wishes" className="flex flex-col gap-2">
          {w.items.map((it) => (
            <WishRow key={it.id} w={w} item={it} />
          ))}
        </ul>
      )}

      {w.is_owner && (
        <section className="glass rounded-[24px] p-4" aria-label="Add a wish">
          <WishForm
            pending={addWish.isPending}
            onSave={(body) => addWish.mutateAsync({ id: w.id, body })}
          />
        </section>
      )}
      {editing && <WishlistEditor list={w} onClose={() => setEditing(false)} />}
    </div>
  );
}
