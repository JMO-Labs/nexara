"use client";
/**
 * @file components/mentions/useComposerMention.ts
 * @brief Tiptap Mention extension wired to the member list; exposes the
 *        open menu state so the composer renders <MentionMenu/>.
 *        Groups the viewer may @-tag follow people ("@slug" notifies the
 *        group). Text output stays "@username" (editor.getText()).
 */
import * as React from "react";
import Mention from "@tiptap/extension-mention";
import { matchMembers, useMembersList } from "@/hooks/useMembersList";
import { useSubgroupList } from "@/hooks/useSubgroups";
import type { Subgroup } from "@/lib/api/subgroups";
import type { UserSummary } from "@/lib/api/users";

type Item = UserSummary & { hint?: string };

interface MenuState {
  items: Item[];
  active: number;
  rect: DOMRect | null;
  pick: (u: Item) => void;
}

/**
 * @brief Groups the viewer may @-tag, shaped as picker entries.
 * @param groups subgroup list
 * @return entries (username = slug)
 */
export function taggableGroups(groups: Subgroup[]): Item[] {
  return groups
    .filter(
      (g) =>
        g.is_member &&
        !g.archived_at &&
        (g.tag_policy !== "admins" ||
          g.my_role === "owner" ||
          g.my_role === "moderator"),
    )
    .map((g) => ({
      id: `g:${g.id}`,
      username: g.slug,
      display_name: g.name,
      avatar_url: g.avatar_url,
      hint: "Group",
    }));
}

/**
 * @brief Mention extension + menu state for one editor.
 * @return { extension, menu } (menu is null when closed)
 */
export function useComposerMention() {
  const { data: members = [] } = useMembersList();
  const { data: groups } = useSubgroupList();
  const membersRef = React.useRef<{ people: UserSummary[]; groups: Item[] }>({
    people: members,
    groups: [],
  });
  React.useEffect(() => {
    membersRef.current = {
      people: members,
      groups: taggableGroups(groups ?? []),
    };
  }, [members, groups]);
  const [menu, setMenu] = React.useState<MenuState | null>(null);

  // Built once; the suggestion callbacks only touch refs/setters at event time.
  // eslint-disable-next-line react-hooks/refs -- refs are read in editor callbacks, not render
  const [extension] = React.useState(() => {
    let current: MenuState | null = null;
    const set = (m: MenuState | null) => {
      current = m;
      setMenu(m);
    };
    return Mention.configure({
      HTMLAttributes: { class: "font-medium text-[var(--nx-blue)]" },
      renderText: ({ node }) => `@${node.attrs.id}`,
      renderHTML: ({ node }) => [
        "span",
        { class: "font-medium text-[var(--nx-blue)]" },
        `@${node.attrs.id}`,
      ],
      suggestion: {
        char: "@",
        items: ({ query }): Item[] => [
          ...matchMembers(membersRef.current.people, query),
          ...matchMembers(membersRef.current.groups, query, 3),
        ],
        render: () => {
          const show = (p: {
            items: Item[];
            command: (a: { id: string; label: string }) => void;
            clientRect?: (() => DOMRect | null) | null;
          }) =>
            set({
              items: p.items,
              active: 0,
              rect: p.clientRect?.() ?? null,
              pick: (u) => p.command({ id: u.username, label: u.display_name }),
            });
          return {
            onStart: show,
            onUpdate: show,
            onExit: () => set(null),
            onKeyDown: ({ event }) => {
              const m = current;
              if (!m || !m.items.length) return false;
              if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                const d = event.key === "ArrowDown" ? 1 : -1;
                set({
                  ...m,
                  active: (m.active + d + m.items.length) % m.items.length,
                });
                return true;
              }
              if (event.key === "Enter" || event.key === "Tab") {
                m.pick(m.items[m.active]);
                return true;
              }
              if (event.key === "Escape") {
                set(null);
                return true;
              }
              return false;
            },
          };
        },
      },
    });
  });
  return { extension, menu };
}
