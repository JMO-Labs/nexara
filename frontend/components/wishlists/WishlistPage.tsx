"use client";
/**
 * @file components/wishlists/WishlistPage.tsx
 * @brief One wishlist: hero, wishes, add form for the list's people, and
 *        edit (wizard in a modal) or delete for its creator.
 */
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, Gift, Pencil, Trash2 } from "lucide-react";
import { Button, EmptyState, Modal, Skeleton } from "@/components/ui";
import { useWishlist, useWishlistActions } from "@/hooks/useWishlists";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { WishForm } from "./WishForm";
import { WishlistHero } from "./WishlistHero";
import { WishRow } from "./WishRow";
import { WishlistWizard } from "./wizard/WishlistWizard";

/**
 * @brief Wishlist detail page body.
 * @param id wishlist id
 * @return page
 */
export function WishlistPage({ id }: { id: string }) {
  const router = useRouter();
  const { data: w, isLoading, isError } = useWishlist(id);
  const { addWish, remove } = useWishlistActions();
  const confirm = useConfirmDialog((s) => s.confirm);
  const [editing, setEditing] = React.useState(false);

  if (isLoading) return <Skeleton height={280} rounded="lg" />;
  if (isError || !w)
    return (
      <EmptyState
        icon={Gift}
        title="Wishlist not found"
        description="It was deleted or isn't shared with you."
      />
    );

  const actions = w.is_owner && (
    <>
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
              message: "The list and its wishes are removed for everyone.",
              confirmLabel: "Delete",
              tone: "danger",
            })
          )
            remove.mutate(w.id, {
              onSuccess: () => router.push("/app/wishlists"),
            });
        }}
      >
        <Trash2 className="size-4" aria-hidden /> Delete
      </Button>
    </>
  );

  return (
    <div className="mx-auto flex w-full max-w-[1000px] flex-col gap-5 pb-8">
      <Link
        href="/app/wishlists"
        className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
      >
        <ChevronLeft className="size-4" aria-hidden /> Wishlists
      </Link>
      <WishlistHero w={w} actions={actions || undefined} />
      {w.items.length === 0 ? (
        <EmptyState
          compact
          icon={Gift}
          title={
            w.can_edit_items ? "Add the first wish" : "Nothing on this list yet"
          }
        />
      ) : (
        <ul aria-label="Wishes" className="flex flex-col gap-2">
          {w.items.map((it) => (
            <WishRow key={it.id} w={w} item={it} />
          ))}
        </ul>
      )}
      {w.can_edit_items && (
        <section className="glass rounded-[26px] p-5" aria-label="Add a wish">
          <WishForm
            currency={w.currency}
            pending={addWish.isPending}
            onSave={(body) => addWish.mutateAsync({ id: w.id, body })}
          />
        </section>
      )}
      {editing && (
        <Modal
          open
          onClose={() => setEditing(false)}
          size="lg"
          title="Edit wishlist"
        >
          <WishlistWizard
            list={w}
            onDone={() => setEditing(false)}
            onCancel={() => setEditing(false)}
          />
        </Modal>
      )}
    </div>
  );
}
