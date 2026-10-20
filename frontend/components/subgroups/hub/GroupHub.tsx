/**
 * @file components/subgroups/hub/GroupHub.tsx
 * @brief Group hub: cover band, tab nav (scrolls horizontally on phone,
 *        vertical on md+), member gate and a scoped chat sidebar.
 */
"use client";

import * as React from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ChevronsLeft, ChevronsRight, MessageSquare } from "lucide-react";
import { Skeleton, EmptyState, Button, IconButton } from "@/components/ui";
import { cn } from "@/lib/utils";
import { useSubgroupDetail } from "@/hooks/useSubgroups";
import { CoverBand } from "./CoverBand";
import { MemberOnlyGate } from "./MemberOnlyGate";
import { GroupChatPanel } from "./GroupChatPanel";
import { getVisibleTabs } from "./tabs";

const CHAT_OPEN_KEY = "nx:groupHub:chatOpen";
const NAV_COLLAPSED_KEY = "nx:groupHub:navCollapsed";

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
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: subgroup, isLoading } = useSubgroupDetail(slug);
  const currentTab = searchParams.get("tab") || "overview";
  const [chatOpen, toggleChat] = usePersistedFlag(CHAT_OPEN_KEY);
  const [navCollapsed, toggleNav] = usePersistedFlag(NAV_COLLAPSED_KEY);

  if (isLoading) {
    return (
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <Skeleton height={320} />
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
        "grid w-full grid-cols-1 motion-safe:transition-[grid-template-columns]",
        chatOpen && "md:grid-cols-[minmax(0,1fr)_400px]",
      )}
    >
      <div className="min-w-0">
        <CoverBand
          subgroup={subgroup}
          right={
            <Button
              size="sm"
              variant="ghost"
              aria-pressed={chatOpen}
              onClick={toggleChat}
              className={cn(
                "min-h-11",
                chatOpen
                  ? "bg-white/20 text-white backdrop-blur hover:bg-white/30"
                  : "bg-white text-black hover:bg-white/90",
              )}
            >
              <MessageSquare className="size-4" aria-hidden />
              {chatOpen ? "Close chat" : "Open chat"}
            </Button>
          }
        />

        <div className="px-4 py-4 md:py-6 md:pl-3 md:pr-8">
          <div
            className={cn(
              "grid grid-cols-1 gap-3 md:gap-5",
              navCollapsed
                ? "md:grid-cols-[56px_1fr]"
                : "md:grid-cols-[180px_1fr]",
            )}
          >
            <div className="min-w-0 md:sticky md:top-24 md:max-h-[calc(100vh-120px)] md:self-start md:overflow-y-auto">
              <div className="mb-1 hidden md:flex md:justify-end">
                <IconButton
                  size="sm"
                  variant="ghost"
                  onClick={toggleNav}
                  aria-label={navCollapsed ? "Expand nav" : "Collapse nav"}
                >
                  {navCollapsed ? (
                    <ChevronsRight className="size-4" aria-hidden />
                  ) : (
                    <ChevronsLeft className="size-4" aria-hidden />
                  )}
                </IconButton>
              </div>
              <nav aria-label="Group sections">
                <ul className="m-0 flex list-none gap-1 overflow-x-auto p-0 [scrollbar-width:none] md:flex-col md:overflow-visible [&::-webkit-scrollbar]:hidden">
                  {visibleTabs.map(({ id, label, Icon }) => {
                    const isActive = active?.id === id;
                    return (
                      <li key={id} className="shrink-0">
                        <button
                          type="button"
                          onClick={() => router.replace(`?tab=${id}`)}
                          aria-current={isActive ? "page" : undefined}
                          title={navCollapsed ? label : undefined}
                          className={cn(
                            "flex min-h-11 w-full items-center gap-2 rounded-xl px-3 text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
                            navCollapsed && "md:justify-center md:px-0",
                            isActive
                              ? "bg-accent font-semibold text-surface-strong"
                              : "hover:bg-surface",
                          )}
                        >
                          <Icon aria-hidden className="size-5 shrink-0" />
                          <span className={cn(navCollapsed && "md:sr-only")}>
                            {label}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </nav>
            </div>

            <section className="min-w-0 rounded-2xl bg-surface p-4 md:p-6">
              {Active ? (
                <Active subgroup={subgroup} />
              ) : active ? (
                <EmptyState title={active.label} description="Coming soon" />
              ) : null}
            </section>
          </div>
        </div>
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
