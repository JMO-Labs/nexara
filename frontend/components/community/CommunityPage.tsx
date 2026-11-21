"use client";
/**
 * @file components/community/CommunityPage.tsx
 * @brief Community page: People / Groups switch bound to ?view=.
 */
import { useRouter, useSearchParams } from "next/navigation";
import { PageHeader, Segmented } from "@/components/ui/page";
import { PeopleDirectory } from "@/components/members/PeopleDirectory";
import { GroupsPage } from "@/components/subgroups/groups-page/GroupsPage";

type View = "people" | "groups";

const VIEWS: { value: View; label: string }[] = [
  { value: "people", label: "People" },
  { value: "groups", label: "Groups" },
];

/**
 * @brief Community page body.
 * @return header, view switch and the selected directory
 */
export function CommunityPage() {
  const router = useRouter();
  const params = useSearchParams();
  const view: View = params.get("view") === "groups" ? "groups" : "people";

  const setView = (v: View) => {
    const next = new URLSearchParams(params.toString());
    if (v === "groups") next.set("view", "groups");
    else next.delete("view");
    router.push(next.toString() ? `/app/community?${next}` : "/app/community");
  };

  return (
    <>
      <PageHeader
        title="Community"
        description="The people and groups you're connected to."
        actions={
          <div className="w-full md:w-auto">
            <Segmented
              label="Community view"
              options={VIEWS}
              value={view}
              onChange={setView}
            />
          </div>
        }
      />
      {view === "groups" ? (
        <GroupsPage embedded />
      ) : (
        <PeopleDirectory embedded />
      )}
    </>
  );
}
