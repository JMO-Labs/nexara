"use client";
/**
 * @file components/members/MemberProfile.tsx
 * @brief Member profile: header plus Photos | Groups tabs.
 */
import * as React from "react";
import { Users } from "lucide-react";
import { PageHeader, Segmented } from "@/components/ui/page";
import { EmptyState } from "@/components/ui/EmptyState";
import { MemberHeader } from "@/components/members/MemberHeader";
import { MemberGroupsTab } from "@/components/members/MemberGroupsTab";
import { MemberGalleriesTab } from "@/components/members/MemberGalleriesTab";
import { useMemberConnection, useMemberProfile } from "@/hooks/useMembers";
import { useSession } from "@/stores/session";
import { statusOf } from "@/components/members/personStatus";

type Tab = "photos" | "groups";

const TABS: { value: Tab; label: string }[] = [
  { value: "photos", label: "Photos" },
  { value: "groups", label: "Groups" },
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
  const p = profile.data;
  const status = connection.data
    ? statusOf(connection.data)
    : p?.last_seen_at
      ? statusOf({ online: false, last_seen_at: p.last_seen_at })
      : "";
  const description = p
    ? `@${p.username}${status ? ` · ${status}` : ""}`
    : undefined;

  if (profile.isLoading) {
    return (
      <div data-testid="profile-skeleton" aria-busy="true">
        <PageHeader title="Profile" back={back} />
        <div className="glass h-44 animate-pulse rounded-[32px]" />
      </div>
    );
  }
  if (profile.isError || !p) {
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
  return (
    <>
      <PageHeader
        title={p.display_name}
        description={description}
        back={back}
      />
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
