/**
 * @file components/subgroups/hub/GroupHub.tsx
 * @brief Group hub: compact cover band, SideNav tabs (horizontal pills on
 *        phone, vertical on md+), Panel content, member gate, scoped chat.
 */
"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { MessageSquare } from "lucide-react";
import { Skeleton, EmptyState, Button } from "@/components/ui";
import { Panel, SideNav, TwoPane } from "@/components/ui/page";
import { cn } from "@/lib/utils";
import { useSubgroupDetail } from "@/hooks/useSubgroups";
import { CoverBand } from "./CoverBand";
import { MemberOnlyGate } from "./MemberOnlyGate";
import { GroupChatPanel } from "./GroupChatPanel";
import { getVisibleTabs } from "./tabs";

const CHAT_OPEN_KEY = "nx:groupHub:chatOpen";

/** Persisted boolean preference (localStorage; safe when unavailable). */
function usePersistedFlag(key: string): [boolean, () => void] {
  const [on, setOn] = React.useState(false);
  React.useEffect(() => {
    try {
      setOn(window.localStorage.getItem(key) === "1");
    } catch {
      /* ignore */
    }
  }, [key]);
  const toggle = React.useCallback(() => {
    setOn((v) => {
      const next = !v;
      try {
        window.localStorage.setItem(key, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }, [key]);
  return [on, toggle];
}

export interface GroupHubProps {
  slug: string;
}

/**
 * @brief Group hub page body.
 * @param slug group slug
 * @return hub view
 */
export function GroupHub({ slug }: GroupHubProps) {
  const searchParams = useSearchParams();
  const { data: subgroup, isLoading } = useSubgroupDetail(slug);
  const currentTab = searchParams.get("tab") || "overview";
  const [chatOpen, toggleChat] = usePersistedFlag(CHAT_OPEN_KEY);

  if (isLoading) {
    return (
      <div className="flex w-full flex-col gap-[18px]">
        <Skeleton height={220} />
        <Skeleton height={200} />
      </div>
    );
  }

  if (!subgroup) {
    return (
      <EmptyState
        title="Group not found"
        description="It may have been deleted."
      />
    );
  }

  // Non-members of restricted groups see gate only.
  const isMember = !!subgroup.my_role;
  const isOpen = subgroup.join_policy === "open";
  if (!isMember && !isOpen) {
    return <MemberOnlyGate subgroup={subgroup} />;
  }

  const visibleTabs = getVisibleTabs(subgroup);
  const active = visibleTabs.find((t) => t.id === currentTab) ?? visibleTabs[0];
  const Active = active?.Component;

  return (
    <div
      className={cn(
        "grid w-full grid-cols-1 gap-[18px] motion-safe:transition-[grid-template-columns]",
        chatOpen && "md:grid-cols-[minmax(0,1fr)_400px]",
      )}
    >
      <div className="min-w-0">
        <CoverBand
          subgroup={subgroup}
          right={
            <Button
              size="sm"
              variant="glass"
              aria-pressed={chatOpen}
              onClick={toggleChat}
            >
              <MessageSquare className="size-4" aria-hidden />
              {chatOpen ? "Close chat" : "Open chat"}
            </Button>
          }
        />

        <TwoPane
          asideWidth={200}
          aside={
            <SideNav
              label="Group sections"
              activeId={active?.id ?? ""}
              items={visibleTabs.map(({ id, label, Icon }) => ({
                id,
                label,
                icon: Icon,
                href: `/app/subgroups/${slug}?tab=${id}`,
              }))}
            />
          }
        >
          <Panel as="section" aria-label={active?.label}>
            {Active ? (
              <Active subgroup={subgroup} />
            ) : active ? (
              <EmptyState title={active.label} description="Coming soon" />
            ) : null}
          </Panel>
        </TwoPane>
      </div>

      {/* Scoped chat: beside content on md+, full-screen overlay on phone. */}
      {chatOpen && (
        <div className="fixed inset-0 z-50 bg-bg md:sticky md:inset-auto md:top-16 md:z-auto md:h-[calc(100vh-4rem)]">
          <GroupChatPanel subgroup={subgroup} onClose={toggleChat} />
        </div>
      )}
    </div>
  );
}

export default GroupHub;
