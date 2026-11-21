"use client";
/**
 * @file components/mentions/useComposerMention.ts
 * @brief Tiptap Mention extension wired to the member list; exposes the
 *        open menu state so the composer renders <MentionMenu/>.
 *        Text output stays "@username" (editor.getText()).
 */
import * as React from "react";
import Mention from "@tiptap/extension-mention";
import { matchMembers, useMembersList } from "@/hooks/useMembersList";
import type { UserSummary } from "@/lib/api/users";

interface MenuState {
  items: UserSummary[];
  active: number;
  rect: DOMRect | null;
  pick: (u: UserSummary) => void;
}

/**
 * @brief Mention extension + menu state for one editor.
 * @return { extension, menu } (menu is null when closed)
 */
export function useComposerMention() {
  const { data: members = [] } = useMembersList();
  const membersRef = React.useRef(members);
  React.useEffect(() => {
    membersRef.current = members;
  }, [members]);
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
        items: ({ query }) => matchMembers(membersRef.current, query),
        render: () => {
          const show = (p: {
            items: UserSummary[];
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
