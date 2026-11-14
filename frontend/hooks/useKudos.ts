"use client";
/**
 * @file hooks/useKudos.ts
 * @brief Kudos wall (infinite) and optimistic send mutation.
 */
import {
  useInfiniteQuery,
  useQueryClient,
  type InfiniteData,
} from "@tanstack/react-query";
import { useMutationWithToast } from "./useMutationWithToast";
import { qk } from "@/lib/query-keys";
import {
  createKudos,
  listKudos,
  type CreateKudosBody,
  type Kudos,
  type KudosPage,
  type KudosRecipient,
} from "@/lib/api/kudos";
import { useSession } from "@/stores/session";

type Wall = InfiniteData<KudosPage, string | undefined>;

/**
 * @brief Cursor-paginated kudos wall.
 * @return infinite query
 */
export function useKudosWall() {
  return useInfiniteQuery({
    queryKey: qk.kudos.wall(),
    queryFn: ({ pageParam }) => listKudos(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) =>
      last.pagination.has_more
        ? (last.pagination.next_cursor ?? undefined)
        : undefined,
  });
}

/**
 * @brief Send kudos; shows the card on the wall at once, reverts on error.
 * @param recipient recipient profile used for the optimistic card
 * @return mutation
 */
export function useSendKudos(recipient: KudosRecipient | null) {
  const qc = useQueryClient();
  const me = useSession((s) => s.user);
  return useMutationWithToast({
    mutationFn: (body: CreateKudosBody) => createKudos(body),
    successKey: "toasts.kudos.sent",
    onMutate: async (body: CreateKudosBody) => {
      await qc.cancelQueries({ queryKey: qk.kudos.wall() });
      const prev = qc.getQueryData<Wall>(qk.kudos.wall());
      const temp: Kudos = {
        id: `optimistic-${Date.now()}`,
        recipient_id: body.recipient_id,
        message: body.message ?? null,
        author_id: me?.id ?? "",
        author_name: me?.display_name ?? null,
        subgroup_id: body.subgroup_id ?? null,
        created_at: new Date().toISOString(),
        recipient,
      };
      if (prev && prev.pages.length > 0) {
        const pages = [...prev.pages];
        pages[0] = { ...pages[0], kudos: [temp, ...pages[0].kudos] };
        qc.setQueryData<Wall>(qk.kudos.wall(), { ...prev, pages });
      }
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.kudos.wall(), ctx.prev);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: qk.kudos.wall() });
      qc.invalidateQueries({ queryKey: qk.home.feed() });
    },
  });
}
