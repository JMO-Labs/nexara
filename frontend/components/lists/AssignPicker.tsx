"use client";
/**
 * @file components/lists/AssignPicker.tsx
 * @brief "Assign" button opening a searchable member picker (popover).
 */
import { useState } from "react";
import { UserPlus } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/Popover";
import { matchMembers, useMembersList } from "@/hooks/useMembersList";

export interface AssignPickerProps {
  /** Item title for the accessible name. */
  title: string;
  disabled?: boolean;
  onPick: (userId: string) => void;
}

/**
 * @brief Member picker; picking a member calls onPick and closes.
 * @param props see AssignPickerProps
 * @return popover with trigger
 */
export function AssignPicker({ title, disabled, onPick }: AssignPickerProps) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const { data } = useMembersList();
  const matches = matchMembers(data ?? [], q, 8);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          size="sm"
          variant="secondary"
          disabled={disabled}
          aria-label={`Assign ${title}`}
        >
          <UserPlus aria-hidden className="size-4" /> Assign
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="flex flex-col gap-2 p-3">
        <Input
          aria-label="Search members"
          placeholder="Search members"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <ul className="flex max-h-56 flex-col gap-1 overflow-y-auto">
          {matches.map((u) => (
            <li key={u.id}>
              <button
                type="button"
                className="glass-item flex w-full items-center gap-2 rounded-[16px] px-3 py-2 text-left text-sm hover:bg-[var(--nx-accent)]/10 focus-visible:outline-2 focus-visible:outline-[var(--nx-accent)]"
                onClick={() => {
                  onPick(u.id);
                  setOpen(false);
                  setQ("");
                }}
              >
                <Avatar
                  size="sm"
                  src={u.avatar_url ?? undefined}
                  name={u.display_name}
                />
                <span className="truncate">{u.display_name}</span>
              </button>
            </li>
          ))}
          {matches.length === 0 && (
            <li className="px-2 py-1 text-sm text-muted">No matches</li>
          )}
        </ul>
      </PopoverContent>
    </Popover>
  );
}
