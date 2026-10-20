/**
 * @file app/app/members/[id]/page.tsx
 * @brief Member profile page with galleries tab.
 */
"use client";

import { useParams, useSearchParams } from "next/navigation";
import { Tabs, TabList, Tab, TabPanel } from "@/components/ui";
import { MemberGalleriesTab } from "@/components/members/MemberGalleriesTab";

const TABS = [{ id: "galleries", label: "Galleries" }];

export default function MemberProfilePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const userId = params.id as string;
  const currentTab = searchParams.get("tab") || "galleries";

  return (
    <div className="mx-auto flex w-full flex-1 flex-col gap-6 px-4 py-4 md:px-6 md:py-6">
      <div>
        <h1 className="text-3xl font-black tracking-tight">Member profile</h1>
        <p className="text-sm text-ink/70">User ID: {userId}</p>
      </div>
      <Tabs value={currentTab}>
        <div className="overflow-x-auto">
          <TabList aria-label="Member sections">
            {TABS.map(({ id, label }) => (
              <Tab key={id} value={id} className="min-h-11">
                {label}
              </Tab>
            ))}
          </TabList>
        </div>
        {TABS.map(({ id }) => (
          <TabPanel key={id} value={id}>
            {id === "galleries" && <MemberGalleriesTab userId={userId} />}
          </TabPanel>
        ))}
      </Tabs>
    </div>
  );
}
