"use client";
/**
 * @file components/lists/pages/ListNewView.tsx
 * @brief /app/lists/new: create-list modal over the page; closing or
 *        creating returns to /app/inbox?view=lists, or back to the group
 *        when opened with ?subgroup=<id>.
 */
import { useRouter, useSearchParams } from "next/navigation";
import { useCommunityId } from "@/hooks/useCommunityId";
import { ListCreateModal } from "../ListCreateModal";
import { LISTS_CRUMB, PageHeader } from "./PageChrome";

/** @brief New list page body. */
export function ListNewView() {
  const router = useRouter();
  const communityId = useCommunityId();
  const subgroupId = useSearchParams().get("subgroup");
  return (
    <div className="flex flex-col gap-6">
      <PageHeader crumbs={[LISTS_CRUMB, { label: "New" }]} title="New list" />
      <ListCreateModal
        open
        communityId={communityId}
        subgroupId={subgroupId}
        onClose={() =>
          subgroupId ? router.back() : router.push("/app/inbox?view=lists")
        }
      />
    </div>
  );
}
