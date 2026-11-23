"use client";
/**
 * @file components/members/MemberProfile.tsx
 * @brief Member profile: banner hero, About card beside Photos | Groups.
 */
import * as React from "react";
import Link from "next/link";
import { ChevronLeft, Users } from "lucide-react";
import { PageHeader, Segmented } from "@/components/ui/page";
import { EmptyState } from "@/components/ui/EmptyState";
import { MemberHeader } from "@/components/members/MemberHeader";
import { AboutCard } from "@/components/members/AboutCard";
import { RelationsCard } from "@/components/relations/RelationsCard";
import { MemberTaggedTab } from "@/components/members/MemberTaggedTab";
import { useSearchParams } from "next/navigation";
import { MemberGroupsTab } from "@/components/members/MemberGroupsTab";
import { MemberFamilyTab } from "@/components/members/MemberFamilyTab";
import { MemberGalleriesTab } from "@/components/members/MemberGalleriesTab";
import { StoriesTab } from "@/components/stories/StoriesTab";
import { useFeature } from "@/hooks/useFeature";
import { WishlistCards } from "@/components/wishlists/WishlistCards";
import { useMemberConnection, useMemberProfile } from "@/hooks/useMembers";
import { useSession } from "@/stores/session";
import { statusOf } from "@/components/members/personStatus";

type Tab = "photos" | "wishlists" | "tagged" | "stories" | "family" | "groups";

const TABS: { value: Tab; label: string }[] = [
  { value: "photos", label: "Photos" },
  { value: "wishlists", label: "Wishlists" },
  { value: "tagged", label: "Tagged" },
  { value: "stories", label: "Stories" },
  { value: "family", label: "Family" },
  { value: "groups", label: "Groups" },
];

/**
 * @brief Profile page body.
 * @param userId member id from the route
 * @return profile UI, skeleton or error state
 */
export function MemberProfile({ userId }: { userId: string }) {
  const initial = useSearchParams().get("tab");
  const storiesOn = useFeature("voice_stories");
  const tabs = TABS.filter((t) => storiesOn || t.value !== "stories");
  const [tab, setTab] = React.useState<Tab>(
    tabs.some((t) => t.value === initial) ? (initial as Tab) : "photos",
  );
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
  const isSelf = viewerId === userId;
  return (
    <div className="mx-auto w-full max-w-[1400px] pb-8">
      <Link
        href={back.href}
        className="mb-3 inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
      >
        <ChevronLeft className="size-4" aria-hidden /> {back.label}
      </Link>
      <MemberHeader
        profile={p}
        connection={connection.data}
        isSelf={isSelf}
        status={status}
      />
      <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)] lg:items-start">
        <div className="lg:sticky lg:top-24">
          <AboutCard profile={p} isSelf={isSelf} />
          <div className="mt-5">
            <RelationsCard userId={userId} isSelf={isSelf} />
          </div>
        </div>
        <div className="min-w-0">
          <Segmented
            label="Profile sections"
            options={tabs}
            value={tab}
            onChange={setTab}
          />
          <div className="mt-4">
            {tab === "photos" ? (
              <MemberGalleriesTab userId={userId} />
            ) : tab === "wishlists" ? (
              <WishlistCards
                query={{ person_id: userId }}
                canCreate={isSelf}
                emptyText={`${p.display_name.split(" ")[0]} has no wishlists you can see`}
              />
            ) : tab === "tagged" ? (
              <MemberTaggedTab
                userId={userId}
                name={p.display_name.split(" ")[0]}
              />
            ) : tab === "stories" && storiesOn ? (
              <StoriesTab
                userId={userId}
                name={p.display_name.split(" ")[0]}
                isSelf={isSelf}
              />
            ) : tab === "family" ? (
              <MemberFamilyTab
                userId={userId}
                name={p.display_name.split(" ")[0]}
              />
            ) : (
              <MemberGroupsTab
                groups={connection.data?.shared_groups ?? []}
                name={p.display_name}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
