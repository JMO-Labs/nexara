"use client";
/**
 * @file components/layout/Sidebar.tsx
 * @brief Collapsible 240px/64px left rail with localStorage persistence.
 * Hides under md breakpoint (mobile uses MobileNav).
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Sheet from "@mui/joy/Sheet";
import IconButton from "@mui/joy/IconButton";
import {
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
} from "@heroicons/react/24/outline";
import { Tooltip } from "@/components/ui/Tooltip";
import { NAV_ITEMS, isNavActive } from "./navItems";

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Load collapsed state from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("nx:sidebar:collapsed");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCollapsed(stored === "true");
    setMounted(true);
  }, []);

  const toggleCollapse = () => {
    const newState = !collapsed;
    setCollapsed(newState);
    localStorage.setItem("nx:sidebar:collapsed", newState.toString());
  };

  // Avoid hydration mismatch: don't render until mounted
  if (!mounted) {
    return null;
  }

  const sidebarWidth = collapsed ? 64 : 240;
  const toggleLabel = collapsed ? "expand sidebar" : "collapse sidebar";

  return (
    <Sheet
      component="nav"
      aria-label="Primary"
      variant="outlined"
      sx={{
        display: { xs: "none", md: "flex" },
        flexDirection: "column",
        width: sidebarWidth,
        transition: "width 220ms cubic-bezier(0.22,1,0.36,1)",
        borderTop: 0,
        borderBottom: 0,
        borderLeft: 0,
        p: 2,
        gap: 0.5,
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 1,
        }}
      >
        {!collapsed && (
          <Typography
            level="title-sm"
            sx={{
              px: 2,
              fontFamily: "var(--font-display)",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "text.tertiary",
            }}
          >
            Nexara
          </Typography>
        )}
        <Tooltip title={toggleLabel} placement="right" enterDelay={700}>
          <IconButton
            size="sm"
            variant="plain"
            onClick={toggleCollapse}
            aria-label={toggleLabel}
            sx={{ ml: "auto" }}
          >
            {collapsed ? (
              <ChevronDoubleRightIcon width={20} height={20} />
            ) : (
              <ChevronDoubleLeftIcon width={20} height={20} />
            )}
          </IconButton>
        </Tooltip>
      </Box>
      <Stack
        spacing={0.25}
        component="ul"
        sx={{ listStyle: "none", m: 0, p: 0 }}
        data-tour="sidebar-nav"
      >
        {NAV_ITEMS.map((item) => {
          const active = isNavActive(pathname, item.href);
          const { Icon } = item;
          return (
            <Box component="li" key={item.href}>
              <Tooltip
                title={item.label}
                placement="right"
                disabled={!collapsed}
                enterDelay={700}
              >
                <Box
                  component={Link}
                  href={item.href}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: collapsed ? "center" : "flex-start",
                    gap: collapsed ? 0 : 1.5,
                    width: "100%",
                    px: collapsed ? 0 : 2,
                    py: 1.25,
                    borderRadius: "md",
                    color: active ? "primary.plainColor" : "text.primary",
                    background: active ? "primary.softBg" : "transparent",
                    fontWeight: active ? 600 : 500,
                    "&:hover": { background: "neutral.softBg" },
                    transition: "all 220ms cubic-bezier(0.22,1,0.36,1)",
                  }}
                >
                  <Icon aria-hidden width={20} height={20} />
                  {!collapsed && <span>{item.label}</span>}
                </Box>
              </Tooltip>
            </Box>
          );
        })}
      </Stack>
    </Sheet>
  );
}
