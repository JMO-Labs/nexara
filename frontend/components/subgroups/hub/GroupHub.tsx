/**
 * @file components/subgroups/hub/GroupHub.tsx
 * @brief Group hub: vertical tab nav, title on cover, member gate, plus a
 *        right-side scoped chat sidebar that can stay open across tabs.
 */
"use client";

import * as React from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import IconButton from "@mui/joy/IconButton";
import {
  ChatBubbleLeftRightIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
} from "@heroicons/react/24/outline";
import { AnimatePresence, motion } from "framer-motion";
import { Skeleton, EmptyState, Button, Tooltip } from "@/components/ui";
import { tabPanelVariants } from "@/components/ui/motion";
import { useSubgroupDetail } from "@/hooks/useSubgroups";
import { CoverBand } from "./CoverBand";
import { MemberOnlyGate } from "./MemberOnlyGate";
import { GroupChatPanel } from "./GroupChatPanel";
import { getVisibleTabs } from "./shadcn/tabs";

const CHAT_OPEN_KEY = "nx:groupHub:chatOpen";
const NAV_COLLAPSED_KEY = "nx:groupHub:navCollapsed";

export interface GroupHubProps {
  slug: string;
}

export function GroupHub({ slug }: GroupHubProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: subgroup, isLoading } = useSubgroupDetail(slug);
  const currentTab = searchParams.get("tab") || "overview";

  // Persist chat-drawer preference across tab switches and navigations.
  const [chatOpen, setChatOpen] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    setChatOpen(window.localStorage.getItem(CHAT_OPEN_KEY) === "1");
  }, []);
  const toggleChat = React.useCallback(() => {
    setChatOpen((v) => {
      const next = !v;
      try {
        window.localStorage.setItem(CHAT_OPEN_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  const [navCollapsed, setNavCollapsed] = React.useState(false);
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    setNavCollapsed(window.localStorage.getItem(NAV_COLLAPSED_KEY) === "1");
  }, []);
  const toggleNav = React.useCallback(() => {
    setNavCollapsed((v) => {
      const next = !v;
      try {
        window.localStorage.setItem(NAV_COLLAPSED_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  if (isLoading) {
    return (
      <Stack spacing={3} sx={{ width: "100%", maxWidth: 1200, mx: "auto" }}>
        <Skeleton height={320} />
        <Skeleton height={200} />
      </Stack>
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

  return (
    <Box
      sx={{
        width: "100%",
        display: "grid",
        gridTemplateColumns: {
          xs: "1fr",
          md: chatOpen ? "minmax(0, 1fr) 400px" : "1fr",
        },
        transition: "grid-template-columns 280ms cubic-bezier(0.22,1,0.36,1)",
      }}
    >
      <Stack sx={{ minWidth: 0 }}>
        <CoverBand
          subgroup={subgroup}
          right={
            <Button
              size="sm"
              variant={chatOpen ? "soft" : "solid"}
              onClick={toggleChat}
              startDecorator={
                <ChatBubbleLeftRightIcon style={{ width: 16, height: 16 }} />
              }
              sx={{
                bgcolor: chatOpen ? "rgba(255,255,255,0.16)" : "#fff",
                color: chatOpen ? "#fff" : "rgba(0,0,0,0.85)",
                backdropFilter: chatOpen ? "blur(6px)" : undefined,
                "&:hover": {
                  bgcolor: chatOpen
                    ? "rgba(255,255,255,0.24)"
                    : "rgba(255,255,255,0.88)",
                },
              }}
            >
              {chatOpen ? "Close chat" : "Open chat"}
            </Button>
          }
        />

        <Box
          sx={{
            pl: { xs: 2, md: 1.5 },
            pr: { xs: 2, md: 4 },
            py: { xs: 2, md: 3 },
            width: "100%",
          }}
        >
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                md: navCollapsed ? "56px 1fr" : "180px 1fr",
              },
              gap: { xs: 0, md: 2.5 },
              transition:
                "grid-template-columns 220ms cubic-bezier(0.22,1,0.36,1)",
            }}
          >
            {/* Vertical tab nav — Sidebar-like style with icons + collapse */}
            <Box
              sx={{
                display: { xs: "none", md: "block" },
                position: "sticky",
                top: "100px",
                maxHeight: "calc(100vh - 120px)",
                overflowY: "auto",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: navCollapsed ? "center" : "flex-end",
                  mb: 0.5,
                }}
              >
                <Tooltip
                  title={navCollapsed ? "expand nav" : "collapse nav"}
                  placement="right"
                  enterDelay={700}
                >
                  <IconButton
                    size="sm"
                    variant="plain"
                    onClick={toggleNav}
                    aria-label={navCollapsed ? "expand nav" : "collapse nav"}
                  >
                    {navCollapsed ? (
                      <ChevronDoubleRightIcon width={18} height={18} />
                    ) : (
                      <ChevronDoubleLeftIcon width={18} height={18} />
                    )}
                  </IconButton>
                </Tooltip>
              </Box>
              <Stack
                role="navigation"
                spacing={0.25}
                component="ul"
                sx={{ listStyle: "none", m: 0, p: 0 }}
              >
                {visibleTabs.map(({ id, label, Icon }) => {
                  const active = currentTab === id;
                  return (
                    <Box component="li" key={id}>
                      <Tooltip
                        title={label}
                        placement="right"
                        disabled={!navCollapsed}
                        enterDelay={700}
                      >
                        <Box
                          component="button"
                          onClick={() => router.replace(`?tab=${id}`)}
                          aria-current={active ? "page" : undefined}
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: navCollapsed
                              ? "center"
                              : "flex-start",
                            gap: navCollapsed ? 0 : 1.5,
                            width: "100%",
                            px: navCollapsed ? 0 : 1.25,
                            py: 1.25,
                            borderRadius: "md",
                            border: "none",
                            background: active
                              ? "primary.softBg"
                              : "transparent",
                            color: active
                              ? "primary.plainColor"
                              : "text.primary",
                            fontWeight: active ? 600 : 500,
                            fontSize: "14px",
                            cursor: "pointer",
                            textAlign: "left",
                            transition: "all 200ms ease",
                            borderLeft:
                              active && !navCollapsed
                                ? "3px solid"
                                : "3px solid transparent",
                            borderLeftColor:
                              active && !navCollapsed
                                ? "primary.500"
                                : "transparent",
                            paddingLeft: navCollapsed ? 0 : "1.0625rem",
                            "&:hover": {
                              background: active
                                ? "primary.softBg"
                                : "neutral.softBg",
                            },
                          }}
                        >
                          <Icon aria-hidden width={20} height={20} />
                          {!navCollapsed && <span>{label}</span>}
                        </Box>
                      </Tooltip>
                    </Box>
                  );
                })}
              </Stack>
            </Box>

            {/* Mobile horizontal tab strip — icon + label chips */}
            <Box
              role="tablist"
              sx={{
                display: { xs: "flex", md: "none" },
                gap: 0.75,
                overflowX: "auto",
                px: 0,
                mb: 1,
                "&::-webkit-scrollbar": { display: "none" },
              }}
            >
              {visibleTabs.map(({ id, label, Icon }) => {
                const active = currentTab === id;
                return (
                  <Box
                    key={id}
                    role="tab"
                    aria-current={active ? "page" : undefined}
                    tabIndex={active ? 0 : -1}
                    onClick={() => router.replace(`?tab=${id}`)}
                    sx={{
                      flexShrink: 0,
                      display: "flex",
                      alignItems: "center",
                      gap: 0.5,
                      px: 1.25,
                      py: 0.75,
                      borderRadius: "sm",
                      cursor: "pointer",
                      fontSize: "13px",
                      fontWeight: active ? 600 : 400,
                      color: active ? "primary.plainColor" : "text.secondary",
                      backgroundColor: active
                        ? "primary.softBg"
                        : "transparent",
                      transition: "background-color 200ms ease",
                      "&:hover": {
                        backgroundColor: active
                          ? "primary.softBg"
                          : "neutral.softBg",
                      },
                    }}
                  >
                    <Icon aria-hidden width={16} height={16} />
                    {label}
                  </Box>
                );
              })}
            </Box>

            {/* Tab content — subtle surface container for visual grouping. */}
            <Box
              role="tabpanel"
              sx={{
                minWidth: 0,
                p: { xs: 2, md: 3 },
                borderRadius: "lg",
                bgcolor: "background.surface",
                border: "1px solid",
                borderColor: "divider",
                boxShadow: "xs",
              }}
            >
              <AnimatePresence mode="wait" initial={false}>
                {(() => {
                  const active =
                    visibleTabs.find((t) => t.id === currentTab) ??
                    visibleTabs[0];
                  if (!active) return null;
                  const Component = active.Component;
                  return (
                    <motion.div
                      key={active.id}
                      variants={tabPanelVariants}
                      initial="initial"
                      animate="animate"
                      exit="exit"
                    >
                      {Component ? (
                        <Component subgroup={subgroup} />
                      ) : (
                        <EmptyState
                          title={active.label}
                          description="Coming soon"
                        />
                      )}
                    </motion.div>
                  );
                })()}
              </AnimatePresence>
            </Box>
          </Box>
        </Box>
      </Stack>

      {/* Right-side scoped chat sidebar (md+ only — stays beside content).
          On xs/sm it overlays full-width when open. */}
      {chatOpen && (
        <Box
          sx={{
            position: { xs: "fixed", md: "sticky" },
            top: { xs: 0, md: "64px" },
            right: 0,
            bottom: 0,
            width: { xs: "100%", md: "auto" },
            height: { xs: "100dvh", md: "calc(100vh - 64px)" },
            zIndex: { xs: 50, md: "auto" },
            bgcolor: "background.body",
          }}
        >
          <GroupChatPanel subgroup={subgroup} onClose={toggleChat} />
        </Box>
      )}
    </Box>
  );
}

export default GroupHub;
