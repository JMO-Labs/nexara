/**
 * @file components/search/GlobalCommandPalette.tsx
 * @brief Command palette with live search integration. Debounces query input,
 *        fetches results, renders with 7 static nav actions, navigates on select.
 */
"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem as CmdItem,
  CommandList,
} from "@/components/ui/shadcn/command";
import { useGlobalSearch } from "@/hooks/useSearch";
import { useUI } from "@/stores/ui";

/** One palette row. */
interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  group: string;
  external?: boolean;
  onSelect: () => void;
}

const NAV_ACTIONS: CommandItem[] = [
  {
    id: "nav-home",
    label: "Home",
    hint: "/app",
    group: "Jump to",
    onSelect: () => {},
  },
  {
    id: "nav-feed",
    label: "Feed",
    hint: "/app",
    group: "Jump to",
    onSelect: () => {},
  },
  {
    id: "nav-chat",
    label: "Chat",
    hint: "/app/chat",
    group: "Jump to",
    onSelect: () => {},
  },
  {
    id: "nav-events",
    label: "Events",
    hint: "/app/events",
    group: "Jump to",
    onSelect: () => {},
  },
  {
    id: "nav-subgroups",
    label: "Subgroups",
    hint: "/app/subgroups",
    group: "Jump to",
    onSelect: () => {},
  },
  {
    id: "nav-galleries",
    label: "Galleries",
    hint: "/app/galleries",
    group: "Jump to",
    onSelect: () => {},
  },
  {
    id: "nav-settings",
    label: "Settings",
    hint: "/app/settings",
    group: "Jump to",
    onSelect: () => {},
  },
];

/** Palette contents; mounted only while open so query state resets on close. */
function PaletteBody() {
  const router = useRouter();
  const setOpen = useUI((s) => s.setCommandPaletteOpen);
  const [query, setQuery] = React.useState("");
  const [debouncedQuery, setDebouncedQuery] = React.useState("");

  const { data, isLoading } = useGlobalSearch(debouncedQuery);

  // Debounce query input by 250ms
  React.useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 250);
    return () => clearTimeout(timer);
  }, [query]);

  const items = React.useMemo<CommandItem[]>(() => {
    const searchItems: CommandItem[] = (data?.items ?? []).map((item) => {
      let href = "";
      if (item.type === "posts") {
        href = `/app/post/${item.id}`;
      } else if (item.type === "users") {
        href = `/app/members?user=${item.id}`;
      } else if (item.type === "events") {
        href = `/app/events?event=${item.id}`;
      } else if (item.type === "comments") {
        href = `/app/post/${item.parent_id}#comment-${item.id}`;
      }
      return {
        id: `${item.type}:${item.id}`,
        label: item.title,
        hint: item.snippet,
        group: item.type.charAt(0).toUpperCase() + item.type.slice(1),
        external: true,
        onSelect: () => {
          router.push(href);
          setOpen(false);
        },
      };
    });

    // Add "no results" sentinel when query is long enough but no results
    if (
      debouncedQuery.trim().length >= 2 &&
      !isLoading &&
      searchItems.length === 0
    ) {
      searchItems.push({
        id: "no-results",
        label: "No matches",
        group: "Search",
        external: true,
        onSelect: () => {},
      });
    }

    // Add navigation items
    const navItems = NAV_ACTIONS.map((nav) => ({
      ...nav,
      onSelect: () => {
        let href = "/app";
        if (nav.id === "nav-feed") href = "/app";
        else if (nav.id === "nav-chat") href = "/app/chat";
        else if (nav.id === "nav-events") href = "/app/events";
        else if (nav.id === "nav-subgroups") href = "/app/subgroups";
        else if (nav.id === "nav-galleries") href = "/app/galleries";
        else if (nav.id === "nav-settings") href = "/app/settings";
        router.push(href);
        setOpen(false);
      },
    }));

    return [...searchItems, ...navItems];
  }, [data?.items, debouncedQuery, isLoading, router, setOpen]);

  // Search results are server-filtered; only filter local nav items.
  const q = query.trim().toLowerCase();
  const visible = items.filter(
    (it) => it.external || !q || it.label.toLowerCase().includes(q),
  );
  const groups = new Map<string, CommandItem[]>();
  for (const it of visible) {
    groups.set(it.group, [...(groups.get(it.group) ?? []), it]);
  }

  return (
    <Command shouldFilter={false}>
      <CommandInput
        aria-label="Command palette"
        placeholder="Search Nexara — try a name, post, or event…"
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        <CommandEmpty>No matches</CommandEmpty>
        {[...groups].map(([group, list]) => (
          <CommandGroup key={group} heading={group}>
            {list.map((it) => (
              <CmdItem key={it.id} value={it.id} onSelect={it.onSelect}>
                <span>{it.label}</span>
                {it.hint && (
                  <span className="ml-auto truncate text-xs text-muted">
                    {it.hint}
                  </span>
                )}
              </CmdItem>
            ))}
          </CommandGroup>
        ))}
      </CommandList>
    </Command>
  );
}

export function GlobalCommandPalette() {
  const open = useUI((s) => s.commandPaletteOpen);
  const setOpen = useUI((s) => s.setCommandPaletteOpen);

  // Cmd/Ctrl+K toggles the palette
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(!useUI.getState().commandPaletteOpen);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  return (
    <CommandDialog open={open} onOpenChange={setOpen} title="Command palette">
      <PaletteBody />
    </CommandDialog>
  );
}
