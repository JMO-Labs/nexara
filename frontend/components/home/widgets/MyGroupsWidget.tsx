"use client";
/**
 * @file components/home/widgets/MyGroupsWidget.tsx
 * @brief Editorial group tiles. Avatar / monogram + name. Up to 6, with a
 *        "+ View all" tile when more exist. Uses Joy theme tokens — no
 *        hard-coded indigo.
 */
import * as React from "react";
import Link from "next/link";
import Box from "@mui/joy/Box";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { EmptyState, Skeleton } from "@/components/ui";
import type { WidgetContext } from "@/lib/widgets/registry";

const tileSx = {
  all: "unset",
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  gap: 1,
  px: 1.25,
  py: 1,
  borderRadius: "md",
  border: "1px solid",
  borderColor: "divider",
  bgcolor: "background.surface",
  transition: "border-color 150ms, transform 150ms",
  "&:hover": {
    borderColor: "primary.500",
    transform: "translateY(-1px)",
  },
  "&:focus-visible": {
    outline: "2px solid var(--nx-palette-focusVisible)",
    outlineOffset: 2,
  },
} as const;

export function MyGroupsWidget(_: WidgetContext) {
  const { data, isLoading } = useSubgroupList();

  if (isLoading) {
    return (
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(3, 1fr)" },
          gap: 1,
        }}
      >
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} height={48} rounded="md" />
        ))}
      </Box>
    );
  }

  const all = (data ?? []).filter((sg) => sg.my_role !== null);
  const groups = all.slice(0, 6);
  const hasMore = all.length > 6;

  if (groups.length === 0) {
    return (
      <EmptyState title="No groups yet" description="Join a group to see it here." />
    );
  }

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(3, 1fr)" },
        gap: 1,
      }}
    >
      {groups.map((sg) => (
        <Box
          key={sg.id}
          component={Link}
          href={`/app/subgroups/${sg.slug}`}
          aria-label={`Go to ${sg.name}`}
          sx={tileSx}
        >
          {sg.avatar_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={sg.avatar_url}
              alt=""
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                objectFit: "cover",
                flexShrink: 0,
              }}
            />
          ) : (
            <Box
              sx={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                bgcolor: "primary.softBg",
                color: "primary.plainColor",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                fontWeight: 600,
                flexShrink: 0,
              }}
            >
              {sg.name.charAt(0).toUpperCase()}
            </Box>
          )}
          <Box
            sx={{
              fontSize: 12,
              fontWeight: 500,
              color: "text.primary",
              minWidth: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {sg.name}
          </Box>
        </Box>
      ))}
      {hasMore && (
        <Box
          component={Link}
          href="/app/subgroups"
          aria-label="View all groups"
          sx={tileSx}
        >
          <Box
            sx={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              bgcolor: "background.level1",
              color: "text.tertiary",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 16,
              fontWeight: 600,
              flexShrink: 0,
            }}
          >
            +
          </Box>
          <Box
            sx={{
              fontSize: 12,
              fontWeight: 500,
              color: "text.secondary",
            }}
          >
            View all
          </Box>
        </Box>
      )}
    </Box>
  );
}

export default MyGroupsWidget;
