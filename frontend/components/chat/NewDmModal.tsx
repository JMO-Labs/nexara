"use client";
/**
 * @file components/chat/NewDmModal.tsx
 * @brief User-picker modal that lists community members, filters by query,
 *        and opens (or creates) a DM channel on selection.
 */
import * as React from "react";
import { Modal, Input, Avatar, Skeleton } from "@/components/ui";
import { useQuery } from "@tanstack/react-query";
import { listUsers, type UserSummary } from "@/lib/api/users";

export interface NewDmModalProps {
  open: boolean;
  onClose: () => void;
  onSelect: (userId: string) => void;
  /** Hide a user (typically the session user). */
  excludeUserId?: string | null;
}

export function NewDmModal({
  open,
  onClose,
  onSelect,
  excludeUserId,
}: NewDmModalProps) {
  const [q, setQ] = React.useState("");

  const usersQ = useQuery({
    queryKey: ["users", "list", "all"],
    queryFn: () => listUsers(null, 100),
    enabled: open,
    staleTime: 60_000,
  });

  const filtered = React.useMemo(() => {
    const base = (usersQ.data?.items ?? []).filter(
      (u) => !excludeUserId || u.id !== excludeUserId,
    );
    const query = q.trim().toLowerCase();
    if (!query) return base;
    return base.filter(
      (u) =>
        u.username.toLowerCase().includes(query) ||
        u.display_name.toLowerCase().includes(query),
    );
  }, [usersQ.data, q, excludeUserId]);

  const select = (u: UserSummary) => {
    onSelect(u.id);
    setQ("");
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="New direct message">
      <div className="flex w-full flex-col gap-3">
        <Input
          autoFocus
          aria-label="Search members"
          placeholder="Search by name or @username"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div className="-mx-2 max-h-[360px] overflow-y-auto">
          {usersQ.isLoading ? (
            <div className="flex flex-col gap-2 px-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} height={48} />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <p className="text-muted p-4 text-center text-sm">
              No matching users.
            </p>
          ) : (
            <ul className="flex flex-col">
              {filtered.map((u) => (
                <li key={u.id}>
                  <button
                    type="button"
                    onClick={() => select(u)}
                    className="hover:bg-bg flex min-h-12 w-full items-center gap-3 rounded-xl px-4 py-2 text-left outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  >
                    <Avatar
                      size="md"
                      src={u.avatar_url ?? undefined}
                      name={u.display_name}
                    />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold">
                        {u.display_name}
                      </span>
                      <span className="text-muted block truncate text-xs">
                        @{u.username}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Modal>
  );
}
