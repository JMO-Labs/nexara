"use client";
/**
 * @file components/lists/pages/ListNewView.tsx
 * @brief /app/lists/new: create-list form inline in a Panel under the page
 *        header. Cancel or create returns to /app/inbox?view=lists, or back
 *        to the group when opened with ?subgroup=<id>.
 */
import { useRouter, useSearchParams } from "next/navigation";
import { Panel } from "@/components/ui/page";
import { useCommunityId } from "@/hooks/useCommunityId";
import { ListCreateForm } from "../ListCreateForm";
import { LISTS_CRUMB, PageHeader } from "./PageChrome";

/** @brief New list page body. */
export function ListNewView() {
  const router = useRouter();
  const communityId = useCommunityId();
  const subgroupId = useSearchParams().get("subgroup");
  const back = () =>
    subgroupId ? router.back() : router.push("/app/inbox?view=lists");
  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        crumbs={[LISTS_CRUMB, { label: "New" }]}
        title="New list"
        description="Start from scratch or from a template."
      />
      <Panel>
        <ListCreateForm
          communityId={communityId}
          subgroupId={subgroupId}
          onDone={back}
          onCancel={back}
        />
      </Panel>
    </div>
  );
}
