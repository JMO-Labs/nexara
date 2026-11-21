/**
 * @file components/search/GlobalCommandPalette.tsx
 * @brief Command palette with live search integration. Debounces query input,
 *        fetches results, renders static jump-to nav actions, navigates on select.
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

const NAV_ACTIONS: { label: string; href: string }[] = [
  { label: "Home", href: "/app" },
  { label: "Chat", href: "/app/chat" },
  { label: "Calendar", href: "/app/events" },
  { label: "Photos", href: "/app/photos" },
  { label: "Community", href: "/app/community" },
  { label: "Groups", href: "/app/community?view=groups" },
  { label: "Inbox", href: "/app/inbox" },
  { label: "Settings", href: "/app/settings" },
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
        href = `/app/members/${item.id}`;
      } else if (item.type === "events") {
        href = `/app/events?event=${item.id}`;
      } else if (item.type === "polls") {
        href = `/app/post/${item.parent_id}`;
      } else if (item.type === "galleries") {
        href = `/app/photos?gallery=${item.id}`;
      } else if (item.type === "subgroups") {
        href = `/app/subgroups/${item.slug ?? item.id}`;
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

    const navItems: CommandItem[] = NAV_ACTIONS.map(({ label, href }) => ({
      id: `nav:${href}`,
      label,
      hint: href,
      group: "Jump to",
      onSelect: () => {
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
    <Command
      shouldFilter={false}
      className="rounded-none bg-transparent text-ink"
    >
      <CommandInput
        aria-label="Command palette"
        placeholder="Search people, posts and events"
        value={query}
        onValueChange={setQuery}
      />
      <CommandList aria-live="polite" className="max-h-[360px] p-1.5">
        <CommandEmpty>No matches</CommandEmpty>
        {[...groups].map(([group, list]) => (
          <CommandGroup key={group} heading={group}>
            {list.map((it) => (
              <CmdItem
                key={it.id}
                value={it.id}
                onSelect={it.onSelect}
                className="group rounded-full px-3.5 py-2 data-[selected=true]:bg-surface-strong data-[selected=true]:text-bg"
              >
                <span>{it.label}</span>
                {it.hint && (
                  <span className="ml-auto truncate text-xs text-muted group-data-[selected=true]:text-bg/70">
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
    <CommandDialog
      open={open}
      onOpenChange={setOpen}
      title="Command palette"
      className="glass rounded-[28px] border-0 bg-[var(--nx-glass-solid)] sm:max-w-xl"
    >
      <PaletteBody />
    </CommandDialog>
  );
}
