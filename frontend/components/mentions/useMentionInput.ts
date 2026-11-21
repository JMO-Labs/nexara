"use client";
/**
 * @file components/mentions/useMentionInput.ts
 * @brief @mention autocomplete for a plain <textarea>/<input>: tracks the
 *        caret, offers matching members, inserts "@username ".
 */
import * as React from "react";
import { matchMembers, useMembersList } from "@/hooks/useMembersList";
import { activeMention } from "@/lib/mentions";
import type { UserSummary } from "@/lib/api/users";

type Field = HTMLTextAreaElement | HTMLInputElement;

/**
 * @brief Mention state for a controlled text field.
 * @param value field text
 * @param setValue setter
 * @param ref field ref (to move the caret after inserting)
 * @return menu items/active/pick plus handlers to spread on the field
 */
export function useMentionInput(
  value: string,
  setValue: (v: string) => void,
  ref: React.RefObject<Field | null>,
) {
  const { data: members = [] } = useMembersList();
  const [caret, setCaret] = React.useState(0);
  const [active, setActive] = React.useState(0);
  const [closedAt, setClosedAt] = React.useState<number | null>(null);
  const m = activeMention(value, caret);
  const items = m && closedAt !== m.start ? matchMembers(members, m.query) : [];
  const idx = Math.min(active, Math.max(items.length - 1, 0));

  const pick = (u: UserSummary) => {
    if (!m) return;
    const before = value.slice(0, m.start);
    const next = `${before}@${u.username} ${value.slice(caret)}`;
    const pos = before.length + u.username.length + 2;
    setValue(next);
    setCaret(pos);
    requestAnimationFrame(() => ref.current?.setSelectionRange(pos, pos));
  };

  const track = (e: React.SyntheticEvent<Field>) =>
    setCaret(e.currentTarget.selectionStart ?? 0);

  /** @return true when the key was used by the menu (caller should stop). */
  const onKeyDown = (e: React.KeyboardEvent<Field>): boolean => {
    if (!items.length) return false;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const d = e.key === "ArrowDown" ? 1 : -1;
      setActive((idx + d + items.length) % items.length);
      return true;
    }
    if (e.key === "Enter" || e.key === "Tab") {
      e.preventDefault();
      pick(items[idx]);
      return true;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      setClosedAt(m!.start);
      return true;
    }
    return false;
  };

  return {
    menu: { items, active: idx, onPick: pick },
    open: items.length > 0,
    onKeyDown,
    fieldProps: { onKeyUp: track, onClick: track, onSelect: track },
    onTextChange: (e: React.ChangeEvent<Field>) => {
      setValue(e.target.value);
      setCaret(e.target.selectionStart ?? e.target.value.length);
      setActive(0);
    },
  };
}
