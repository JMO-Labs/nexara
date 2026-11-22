"use client";
/**
 * @file components/wishlists/WishlistEditor.tsx
 * @brief Create or edit a wishlist: title, occasion, date, who it's for
 *        (you or a household member/pet you manage) and who can see it.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Button, Input, Modal, Textarea } from "@/components/ui";
import { useUserHousehold } from "@/hooks/useHousehold";
import { useWishlistActions } from "@/hooks/useWishlists";
import { useSession } from "@/stores/session";
import { LEVEL_LABEL, type ProfileLevel } from "@/lib/profile";
import {
  OCCASION_LABEL,
  type Occasion,
  type Wishlist,
} from "@/lib/api/wishlists";

const select =
  "glass-item h-10 rounded-full px-3 text-sm focus-visible:outline-2 focus-visible:outline-accent";

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="font-medium">{label}</span>
      {children}
    </label>
  );
}

/**
 * @brief Wishlist form in a modal.
 * @param list existing list, or null to create
 * @param householdId preselect "for" on create
 * @param onClose close handler
 * @return modal
 */
export function WishlistEditor({
  list,
  householdId,
  onClose,
}: {
  list: Wishlist | null;
  householdId?: string;
  onClose: () => void;
}) {
  const router = useRouter();
  const me = useSession((s) => s.user?.id);
  const { data: household = [] } = useUserHousehold(list ? undefined : me);
  const { create, update } = useWishlistActions();
  const [f, setF] = React.useState({
    title: list?.title ?? "",
    occasion: list?.occasion ?? ("birthday" as Occasion),
    occasion_date: list?.occasion_date ?? "",
    note: list?.note ?? "",
    visibility: list?.visibility ?? ("groups" as ProfileLevel),
    household_id: list?.household?.id ?? householdId ?? "",
  });
  const [error, setError] = React.useState<string | null>(null);
  const set = (p: Partial<typeof f>) => setF((o) => ({ ...o, ...p }));

  const save = (e: React.FormEvent) => {
    e.preventDefault();
    if (!f.title.trim()) return setError("Give the list a name.");
    const body = {
      title: f.title.trim(),
      occasion: f.occasion,
      occasion_date: f.occasion_date || null,
      note: f.note.trim() || null,
      visibility: f.visibility,
    };
    const onError = (err: unknown) =>
      setError(err instanceof Error ? err.message : "Couldn't save.");
    if (list)
      update.mutate({ id: list.id, body }, { onSuccess: onClose, onError });
    else
      create.mutate(
        { ...body, household_id: f.household_id || null },
        {
          onSuccess: (w) => {
            onClose();
            router.push(`/app/wishlists/${w.id}`);
          },
          onError,
        },
      );
  };

  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      title={list ? "Edit wishlist" : "New wishlist"}
      description="You'll never see who is getting what, so gifts stay a surprise."
    >
      <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Row label="Name">
            <Input
              value={f.title}
              maxLength={120}
              required
              placeholder="Biscuit turns 5"
              onChange={(e) => set({ title: e.target.value })}
            />
          </Row>
        </div>
        <Row label="Occasion">
          <select
            className={select}
            value={f.occasion}
            onChange={(e) => set({ occasion: e.target.value as Occasion })}
          >
            {(Object.keys(OCCASION_LABEL) as Occasion[]).map((o) => (
              <option key={o} value={o}>
                {OCCASION_LABEL[o]}
              </option>
            ))}
          </select>
        </Row>
        <Row label="Date">
          <Input
            type="date"
            value={f.occasion_date}
            onChange={(e) => set({ occasion_date: e.target.value })}
          />
        </Row>
        {!list && (
          <Row label="Who it's for">
            <select
              className={select}
              value={f.household_id}
              onChange={(e) => set({ household_id: e.target.value })}
            >
              <option value="">Me</option>
              {household.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name}
                </option>
              ))}
            </select>
          </Row>
        )}
        <Row label="Who can see it">
          <select
            className={select}
            value={f.visibility}
            onChange={(e) =>
              set({ visibility: e.target.value as ProfileLevel })
            }
          >
            {(Object.keys(LEVEL_LABEL) as ProfileLevel[]).map((l) => (
              <option key={l} value={l}>
                {LEVEL_LABEL[l]}
              </option>
            ))}
          </select>
        </Row>
        <div className="sm:col-span-2">
          <Row label="Note for gift-givers">
            <Textarea
              rows={2}
              maxLength={500}
              placeholder="Sizes, favorite colors, things to avoid"
              value={f.note}
              onChange={(e) => set({ note: e.target.value })}
            />
          </Row>
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive sm:col-span-2">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2 sm:col-span-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={create.isPending || update.isPending}>
            {list ? "Save changes" : "Create wishlist"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
