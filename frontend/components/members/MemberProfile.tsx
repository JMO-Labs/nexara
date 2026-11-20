"use client";
/**
 * @file components/members/MemberProfile.tsx
 * @brief Member profile: header plus Photos | Groups tabs.
 */
import * as React from "react";
import { Image as ImageIcon, Users } from "lucide-react";
import { PageHeader, Segmented } from "@/components/ui/page";
import { EmptyState } from "@/components/ui/EmptyState";
import { MemberHeader } from "@/components/members/MemberHeader";
import { MemberGroupsTab } from "@/components/members/MemberGroupsTab";
import { MemberGalleriesTab } from "@/components/members/MemberGalleriesTab";
import { useMemberConnection, useMemberProfile } from "@/hooks/useMembers";
import { useSession } from "@/stores/session";

type Tab = "photos" | "groups";

const TABS: { value: Tab; label: string; icon: typeof Users }[] = [
  { value: "photos", label: "Photos", icon: ImageIcon },
  { value: "groups", label: "Groups", icon: Users },
];

/**
 * @brief Profile page body.
 * @param userId member id from the route
 * @return profile UI, skeleton or error state
 */
export function MemberProfile({ userId }: { userId: string }) {
  const [tab, setTab] = React.useState<Tab>("photos");
  const viewerId = useSession((s) => s.user?.id);
  const profile = useMemberProfile(userId);
  const connection = useMemberConnection(userId, profile.data?.username);
  const back = { href: "/app/community", label: "Community" };

  if (profile.isLoading) {
    return (
      <div data-testid="profile-skeleton" aria-busy="true">
        <PageHeader title="Profile" back={back} />
        <div className="glass h-44 animate-pulse rounded-[32px]" />
      </div>
    );
  }
  if (profile.isError || !profile.data) {
    return (
      <>
        <PageHeader title="Profile" back={back} />
        <EmptyState
          icon={Users}
          title="Member not found"
          description="This profile doesn't exist or isn't available to you."
        />
      </>
    );
  }
  const p = profile.data;
  return (
    <>
      <PageHeader title="Profile" back={back} />
      <MemberHeader
        profile={p}
        connection={connection.data}
        isSelf={viewerId === userId}
      />
      <div className="mt-4">
        <Segmented
          label="Profile sections"
          options={TABS}
          value={tab}
          onChange={setTab}
        />
      </div>
      <div className="mt-4">
        {tab === "photos" ? (
          <MemberGalleriesTab userId={userId} />
        ) : (
          <MemberGroupsTab
            groups={connection.data?.shared_groups ?? []}
            name={p.display_name}
          />
        )}
      </div>
    </>
  );
}
