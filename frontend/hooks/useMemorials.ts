"use client";
/**
 * @file hooks/useMemorials.ts
 * @brief Mutations for memorials (admin account memorialize / restore,
 *        household passed-on date).
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMutationWithToast } from "./useMutationWithToast";
import { qk } from "@/lib/query-keys";
import {
  memorializeUser,
  setPassedOn,
  unmemorializeUser,
} from "@/lib/api/memorials";

/** @brief Admin: memorialize a user (passed-on date optional). */
export const useMemorializeUser = () => {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (v: { userId: string; passedOn: string | null }) =>
      memorializeUser(v.userId, v.passedOn),
    successKey: "toasts.admin.user.memorialized",
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.admin.users() }),
  });
};

/** @brief Admin: restore a memorialized user. */
export const useUnmemorializeUser = () => {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (userId: string) => unmemorializeUser(userId),
    successKey: "toasts.admin.user.restored",
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.admin.users() }),
  });
};

/** @brief Set or clear a household member's passed-on date. */
export const useSetPassedOn = (memberId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (passedOn: string | null) => setPassedOn(memberId, passedOn),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["household"] }),
  });
};
