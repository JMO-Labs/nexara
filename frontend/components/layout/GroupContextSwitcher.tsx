"use client";
/**
 * @file components/layout/GroupContextSwitcher.tsx
 * @brief Unobtrusive group context switcher in TopBar. Hidden if 0 groups.
 *        Shows active group name on /app/subgroups/[slug] routes.
 *        Shows "Groups ▾" for ≥2 groups otherwise.
 */
import * as React from "react";
import { useRouter, usePathname } from "next/navigation";
import Menu from "@mui/joy/Menu";
import MenuItem from "@mui/joy/MenuItem";
import MenuButton from "@mui/joy/MenuButton";
import Dropdown from "@mui/joy/Dropdown";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import ListDivider from "@mui/joy/ListDivider";
import Box from "@mui/joy/Box";
import Link from "next/link";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { gradientFor, monogram } from "@/lib/groupVisuals";
import type { Subgroup } from "@/lib/api/subgroups";

export function GroupContextSwitcher() {
  const router = useRouter();
  const pathname = usePathname();
  const { data: groups = [] } = useSubgroupList();

  // Detect active group from path /app/subgroups/<slug>
  const groupSlugMatch = pathname.match(/^\/app\/subgroups\/([^/?]+)/);
  const activeGroupSlug = groupSlugMatch?.[1] ?? null;
  const activeGroup = activeGroupSlug
    ? groups.find((g) => g.slug === activeGroupSlug)
    : null;

  // Visibility rules
  if (groups.length === 0) {
    return null;
  }
  if (groups.length === 1 && !activeGroup) {
    return null;
  }

  // Determine button text
  const buttonText = activeGroup ? `${activeGroup.name} ▾` : "Groups ▾";

  const handleSelectGroup = (slug: string) => {
    router.push(`/app/subgroups/${slug}`);
  };

  return (
    <Dropdown>
      <MenuButton
        slots={{ root: "button" }}
        slotProps={{
          root: {
            "aria-label": "Switch group context",
            "aria-haspopup": "menu",
            style: {
              background: "transparent",
              border: 0,
              padding: "6px 8px",
              cursor: "pointer",
            },
          },
        }}
        variant="plain"
        color="neutral"
        size="sm"
      >
        <Typography level="body-sm">{buttonText}</Typography>
      </MenuButton>
      <Menu
        placement="bottom-start"
        sx={{
          minWidth: 240,
          maxHeight: 400,
          overflowY: "auto",
        }}
      >
        {/* Group list, grouped by parent with indent */}
        {groups.map((g) => (
          <MenuItem
            key={g.id}
            onClick={() => handleSelectGroup(g.slug)}
            sx={{
              pl: g.parent_id ? 4 : 2,
              display: "flex",
              alignItems: "center",
              gap: 1.5,
            }}
          >
            {/* Monogram avatar */}
            <Box
              sx={{
                width: 32,
                height: 32,
                borderRadius: "99px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "0.75rem",
                fontWeight: 600,
                color: "#333",
                background: gradientFor(g.slug).monogramBg,
              }}
            >
              {monogram(g.name)}
            </Box>
            <Stack sx={{ flex: 1, gap: 0 }}>
              <Typography level="body-sm" sx={{ fontWeight: 500 }}>
                {g.name}
              </Typography>
            </Stack>
          </MenuItem>
        ))}

        <ListDivider />

        {/* Footer link to all groups */}
        <MenuItem
          component={Link}
          href="/app/subgroups"
          sx={{ justifyContent: "center" }}
        >
          <Typography level="body-xs" sx={{ opacity: 0.7 }}>
            All groups →
          </Typography>
        </MenuItem>
      </Menu>
    </Dropdown>
  );
}
