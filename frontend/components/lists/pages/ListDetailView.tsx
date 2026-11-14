"use client";
/**
 * @file components/lists/pages/ListDetailView.tsx
 * @brief /app/lists/[id] (detail panel) and /app/lists/[id]/edit (edit
 *        modal); both load the list via useList.
 */
import type { ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Pencil } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useCommunityId } from "@/hooks/useCommunityId";
import { useList } from "@/hooks/useListDetail";
import type { List } from "@/lib/api/listTypes";
import { ListDetailPanel } from "../ListDetailPanel";
import { ListEditModal } from "../ListEditModal";
import { ErrorCard, LISTS_CRUMB, PageHeader, PageSkeleton } from "./PageChrome";

/**
 * @brief Load a list and render loading/error states or children.
 * @param props list id and render function
 * @return state UI or children(list)
 */
function WithList({
  id,
  children,
}: {
  id: string;
  children: (list: List, communityId: string) => ReactNode;
}) {
  const communityId = useCommunityId();
  const { data, isLoading, error } = useList(communityId, id);
  if (isLoading) return <PageSkeleton />;
  if (error || !data)
    return <ErrorCard message="We couldn't load this list." />;
  return <>{children(data, communityId)}</>;
}

/**
 * @brief List detail page body.
 * @param props list id
 * @return page
 */
export function ListDetailView({ id }: { id: string }) {
  return (
    <WithList id={id}>
      {(list, communityId) => (
        <div className="flex flex-col gap-6">
          <PageHeader
            crumbs={[LISTS_CRUMB, { label: list.title }]}
            title={list.title}
            hideTitle
            actions={
              <Button asChild variant="outline">
                <Link href={`/app/lists/${list.id}/edit`}>
                  <Pencil aria-hidden className="size-4" />
                  Edit
                </Link>
              </Button>
            }
          />
          <ListDetailPanel list={list} communityId={communityId} />
        </div>
      )}
    </WithList>
  );
}

/**
 * @brief List edit page body; closing returns to the detail page.
 * @param props list id
 * @return page
 */
export function ListEditView({ id }: { id: string }) {
  const router = useRouter();
  return (
    <WithList id={id}>
      {(list, communityId) => (
        <div className="flex flex-col gap-6">
          <PageHeader
            crumbs={[
              LISTS_CRUMB,
              { label: list.title, href: `/app/lists/${list.id}` },
              { label: "Edit" },
            ]}
            title="Edit list"
          />
          <ListEditModal
            open
            list={list}
            communityId={communityId}
            onClose={() => router.push(`/app/lists/${list.id}`)}
          />
        </div>
      )}
    </WithList>
  );
}
