"use client";
/**
 * @file hooks/useWishlists.ts
 * @brief Wishlist queries and mutations (every write refreshes all wishlists).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addWish,
  claimWish,
  createWishlist,
  deleteWish,
  deleteWishlist,
  getWishlist,
  listWishlists,
  releaseWish,
  updateWish,
  updateWishlist,
  type WishInput,
  type WishlistInput,
  type WishlistQuery,
} from "@/lib/api/wishlists";

const KEY = ["wishlists"] as const;

/** @brief Wishlists the viewer may see, optionally one person's or pet's. */
export const useWishlists = (q: WishlistQuery = {}) =>
  useQuery({
    queryKey: [...KEY, "list", q],
    queryFn: () => listWishlists(q),
    staleTime: 30_000,
  });

/** @brief One wishlist with items. */
export const useWishlist = (id: string) =>
  useQuery({
    queryKey: [...KEY, id],
    queryFn: () => getWishlist(id),
    retry: false,
  });

/** @brief All wishlist writes. */
export function useWishlistActions() {
  const qc = useQueryClient();
  const done = () => void qc.invalidateQueries({ queryKey: KEY });
  const m = <A>(fn: (a: A) => Promise<unknown>) => ({
    mutationFn: fn,
    onSuccess: done,
  });
  return {
    create: useMutation({ mutationFn: createWishlist, onSuccess: done }),
    update: useMutation(
      m((a: { id: string; body: WishlistInput }) =>
        updateWishlist(a.id, a.body),
      ),
    ),
    remove: useMutation(m(deleteWishlist)),
    addWish: useMutation(
      m((a: { id: string; body: WishInput }) => addWish(a.id, a.body)),
    ),
    updateWish: useMutation(
      m((a: { id: string; itemId: string; body: WishInput }) =>
        updateWish(a.id, a.itemId, a.body),
      ),
    ),
    deleteWish: useMutation(
      m((a: { id: string; itemId: string }) => deleteWish(a.id, a.itemId)),
    ),
    claim: useMutation(
      m(
        (a: {
          id: string;
          itemId: string;
          qty?: number;
          amount_cents?: number;
        }) =>
          claimWish(a.id, a.itemId, {
            qty: a.qty,
            amount_cents: a.amount_cents,
          }),
      ),
    ),
    release: useMutation(
      m((a: { id: string; itemId: string }) => releaseWish(a.id, a.itemId)),
    ),
  };
}
