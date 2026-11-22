"use client";
/**
 * @file hooks/useHousehold.ts
 * @brief Queries/mutations for household members and pets.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createHouseholdMember,
  deleteHouseholdMember,
  getHouseholdMember,
  listHousehold,
  listUserHousehold,
  upcomingCelebrations,
  updateHouseholdMember,
  type HouseholdInput,
} from "@/lib/api/household";

const KEY = ["household"] as const;

/** @brief Every member/pet the viewer may see (tag picker). */
export const useVisibleHousehold = () =>
  useQuery({
    queryKey: [...KEY, "all"],
    queryFn: listHousehold,
    staleTime: 60_000,
  });

/** @brief One user's household as the viewer may see it. */
export const useUserHousehold = (userId: string | undefined) =>
  useQuery({
    queryKey: [...KEY, "user", userId],
    queryFn: () => listUserHousehold(userId!),
    enabled: !!userId,
  });

/** @brief One member. */
export const useHouseholdMember = (id: string) =>
  useQuery({
    queryKey: [...KEY, id],
    queryFn: () => getHouseholdMember(id),
    retry: false,
  });

/** @brief Birthdays and gotcha days in the next 14 days. */
export const useCelebrations = () =>
  useQuery({
    queryKey: [...KEY, "upcoming"],
    queryFn: upcomingCelebrations,
    staleTime: 5 * 60_000,
  });

/** @brief Create, update or delete; refreshes every household query. */
export function useSaveHousehold() {
  const qc = useQueryClient();
  const done = () => void qc.invalidateQueries({ queryKey: KEY });
  return {
    create: useMutation({ mutationFn: createHouseholdMember, onSuccess: done }),
    update: useMutation({
      mutationFn: ({ id, body }: { id: string; body: HouseholdInput }) =>
        updateHouseholdMember(id, body),
      onSuccess: done,
    }),
    remove: useMutation({ mutationFn: deleteHouseholdMember, onSuccess: done }),
  };
}
