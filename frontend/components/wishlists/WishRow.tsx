"use client";
/**
 * @file components/wishlists/WishRow.tsx
 * @brief One wish: shop preview, price (flagged outside the suggested
 *        spend), fund progress, and the viewer's actions (edit for the
 *        list's people; claim, pledge, undo for givers).
 */
import * as React from "react";
import {
  ExternalLink,
  Info,
  Pencil,
  PiggyBank,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { formatDistanceToNowStrict } from "date-fns";
import { Button, IconButton } from "@/components/ui";
import { Tooltip } from "@/components/ui/Tooltip";
import { useWishlistActions } from "@/hooks/useWishlists";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { API_BASE } from "@/lib/auth/session";
import { formatMoney } from "@/lib/money";
import { isHttpUrl } from "@/lib/profile";
import type { Wish, WishlistDetail } from "@/lib/api/wishlists";
import { SplitGiftButton } from "@/components/expenses/SplitGiftButton";
import { WishForm } from "./WishForm";
import { MoneyInput } from "./wizard/fields";

function outsideBudget(w: WishlistDetail, item: Wish): boolean {
  const p = item.price_cents;
  if (p == null || item.kind === "fund") return false;
  return (
    (w.budget_min_cents != null && p < w.budget_min_cents) ||
    (w.budget_max_cents != null && p > w.budget_max_cents)
  );
}

function FundPledge({ w, item }: { w: WishlistDetail; item: Wish }) {
  const { claim, release } = useWishlistActions();
  const [amount, setAmount] = React.useState<number | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  if (item.mine)
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-[var(--nx-ok)]">
          You pledged {formatMoney(item.mine, w.currency)}
        </span>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => release.mutate({ id: w.id, itemId: item.id })}
        >
          Undo
        </Button>
      </div>
    );
  return (
    <form
      className="flex flex-col items-end gap-1"
      onSubmit={(e) => {
        e.preventDefault();
        if (!amount) return setError("Enter an amount.");
        claim.mutate(
          { id: w.id, itemId: item.id, amount_cents: amount },
          {
            onError: (err) =>
              setError(err instanceof Error ? err.message : "Couldn't pledge."),
          },
        );
      }}
    >
      <div className="flex items-center gap-2">
        <div className="w-32">
          <MoneyInput
            label={`Pledge to ${item.name}`}
            currency={w.currency}
            cents={amount}
            onChange={setAmount}
            placeholder="Amount"
          />
        </div>
        <Button size="sm" type="submit" loading={claim.isPending}>
          Pledge
        </Button>
      </div>
      {error && (
        <span role="alert" className="text-xs text-destructive">
          {error}
        </span>
      )}
    </form>
  );
}

function GiftClaim({ w, item }: { w: WishlistDetail; item: Wish }) {
  const { claim, release } = useWishlistActions();
  const [error, setError] = React.useState<string | null>(null);
  const mine = item.mine ?? 0;
  const left = item.qty - (item.claimed ?? 0);
  const busy = claim.isPending || release.isPending;
  const take = (qty: number) =>
    claim.mutate(
      { id: w.id, itemId: item.id, qty },
      {
        onError: (err) =>
          setError(err instanceof Error ? err.message : "Couldn't claim."),
      },
    );
  return (
    <div className="flex flex-col items-end gap-1">
      {mine > 0 ? (
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
      ) : left <= 0 ? (
        <span className="text-sm text-muted">Someone has this</span>
      ) : (
        <Button size="sm" disabled={busy} onClick={() => take(1)}>
          I&apos;ll get this
        </Button>
      )}
      {error && (
        <span role="alert" className="text-xs text-destructive">
          {error}
        </span>
      )}
    </div>
  );
}

/**
 * @brief Wish row.
 * @param w list (permissions, currency, budget)
 * @param item the wish
 * @return list item
 */
export function WishRow({ w, item }: { w: WishlistDetail; item: Wish }) {
  const { updateWish, deleteWish } = useWishlistActions();
  const confirm = useConfirmDialog((s) => s.confirm);
  const [editing, setEditing] = React.useState(false);
  const [imgFailed, setImgFailed] = React.useState(false);
  if (editing)
    return (
      <li className="glass-item rounded-[22px] p-4">
        <WishForm
          wish={item}
          currency={w.currency}
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
  const fund = item.kind === "fund";
  const left = item.claimed == null ? null : item.qty - item.claimed;
  const pct =
    fund && item.goal_cents && item.claimed != null
      ? Math.min(100, Math.round((item.claimed / item.goal_cents) * 100))
      : null;
  const img = item.preview?.has_image && !imgFailed;
  // Amazon's API links must be used unchanged (partner tag); else the wish link.
  const link = item.link || item.preview?.buy_url || item.url;
  const checked = item.preview?.checked_at
    ? formatDistanceToNowStrict(new Date(item.preview.checked_at), {
        addSuffix: true,
      })
    : null;
  const liveNote =
    item.price_auto && checked
      ? `Price from ${item.preview?.site_name ?? "the shop"}, checked ${checked}.${
          item.preview?.site_name === "Amazon" ? " It may differ for you." : ""
        }`
      : null;
  return (
    <li className="glass-item flex flex-col gap-3 rounded-[22px] p-4 sm:flex-row sm:items-center">
      <span
        aria-hidden
        className="grid size-16 shrink-0 place-items-center overflow-hidden rounded-[16px] bg-[color-mix(in_srgb,var(--nx-blue)_22%,transparent)]"
      >
        {img ? (
          // eslint-disable-next-line @next/next/no-img-element -- proxied preview image
          <img
            src={`${API_BASE}/api/v1/link-previews/${encodeURIComponent(item.preview!.id)}/image`}
            alt=""
            loading="lazy"
            className="size-full object-cover"
            onError={() => setImgFailed(true)}
          />
        ) : fund ? (
          <PiggyBank className="size-6 text-[var(--nx-accent)]" />
        ) : (
          <span className="text-xl font-semibold text-[var(--nx-accent)]">
            {item.name.slice(0, 1).toUpperCase()}
          </span>
        )}
      </span>
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-baseline gap-x-2 font-medium">
          {link && isHttpUrl(link) ? (
            <a
              href={link}
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
          {item.price_cents != null && (
            <span className="inline-flex items-center gap-1 text-sm text-muted">
              {formatMoney(item.price_cents, w.currency)}
              {liveNote && (
                <Tooltip content={liveNote}>
                  <button
                    type="button"
                    aria-label={liveNote}
                    className="grid size-5 place-items-center rounded-full text-muted outline-none hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
                  >
                    <RefreshCw className="size-3" aria-hidden />
                  </button>
                </Tooltip>
              )}
              {outsideBudget(w, item) && (
                <Tooltip content="Outside the suggested spend">
                  <button
                    type="button"
                    aria-label="Outside the suggested spend"
                    className="grid size-5 place-items-center rounded-full text-muted outline-none hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
                  >
                    <Info className="size-3.5" aria-hidden />
                  </button>
                </Tooltip>
              )}
            </span>
          )}
          {!fund && item.qty > 1 && (
            <span className="text-sm text-muted">
              {left !== null
                ? `${Math.max(left, 0)} of ${item.qty} left`
                : `× ${item.qty}`}
            </span>
          )}
        </p>
        {item.preview?.site_name && (
          <p className="text-xs text-muted">{item.preview.site_name}</p>
        )}
        {item.notes && <p className="text-sm text-muted">{item.notes}</p>}
        {fund && item.goal_cents != null && (
          <div className="mt-2 flex flex-col gap-1">
            {pct != null && (
              <span
                role="progressbar"
                aria-label={`${item.name} funded`}
                aria-valuenow={pct}
                aria-valuemin={0}
                aria-valuemax={100}
                className="block h-2 overflow-hidden rounded-full bg-[color-mix(in_srgb,var(--nx-ink)_10%,transparent)]"
              >
                <span
                  className="block h-full rounded-full bg-[var(--nx-sun)] transition-[width] duration-500 motion-reduce:transition-none"
                  style={{ width: `${pct}%` }}
                />
              </span>
            )}
            <span className="text-xs text-muted">
              {item.claimed != null
                ? `${formatMoney(item.claimed, w.currency)} of `
                : "Goal "}
              {formatMoney(item.goal_cents, w.currency)}
            </span>
          </div>
        )}
        {item.claimers && item.claimers.length > 0 && (
          <p className="mt-1 text-xs text-muted">
            {item.claimers
              .map((c) =>
                fund && c.amount_cents
                  ? `${c.name} (${formatMoney(c.amount_cents, w.currency)})`
                  : c.qty > 1
                    ? `${c.name} × ${c.qty}`
                    : c.name,
              )
              .join(", ")}
          </p>
        )}
      </div>
      {w.can_edit_items && (
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
      )}
      {w.sees_claims &&
        (fund ? (
          <FundPledge w={w} item={item} />
        ) : (
          <>
            <GiftClaim w={w} item={item} />
            <SplitGiftButton itemId={item.id} name={item.name} />
          </>
        ))}
    </li>
  );
}
