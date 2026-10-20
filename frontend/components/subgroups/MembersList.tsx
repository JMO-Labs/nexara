"use client";
/**
 * @file components/subgroups/MembersList.tsx
 * @brief List subgroup members with role pills + admin actions.
 */
import * as React from "react";
import { MoreVertical } from "lucide-react";
import {
  Avatar,
  Badge,
  Button,
  IconButton,
  Skeleton,
  EmptyState,
} from "@/components/ui";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/shadcn/dropdown-menu";
import {
  useSubgroupMembers,
  useRemoveMember,
  useChangeRole,
} from "@/hooks/useSubgroups";
import { useConfirmDialog } from "@/stores/confirmDialog";
import type { Membership } from "@/lib/api/subgroups";

export interface MembersListProps {
  slug: string;
  canManage?: boolean;
  viewerRole?: "owner" | "moderator" | "member" | null;
  onAdd?: () => void;
}

function MemberRow({
  m,
  members,
  canManage,
  viewerRole,
  onRemove,
  onPromote,
  onDemote,
  busy,
}: {
  m: Membership;
  members: Membership[];
  canManage?: boolean;
  viewerRole?: "owner" | "moderator" | "member" | null;
  onRemove?: () => void;
  onPromote?: (role: "moderator" | "owner") => void;
  onDemote?: (role: "moderator") => void;
  busy?: boolean;
}) {
  const confirm = useConfirmDialog((s) => s.confirm);
  const ownerCount = members.filter((mem) => mem.role === "owner").length;
  const isOnlyOwner = m.role === "owner" && ownerCount === 1;
  const canPromoteToOwner = viewerRole === "owner";
  const canPromote =
    (m.role === "member" && canManage) ||
    (m.role === "moderator" && canPromoteToOwner);
  const canDemote = m.role === "moderator" && canManage;
  const canDemoteOwner =
    m.role === "owner" && viewerRole === "owner" && !isOnlyOwner;

  return (
    <div className="flex items-center gap-3 border-b border-current/10 py-2">
      <Avatar
        src={m.avatar_url ?? undefined}
        name={m.display_name ?? m.username ?? m.user_id}
      />
      <div className="min-w-0 flex-1">
        <p className="truncate text-base">
          {m.display_name ?? m.username ?? m.user_id}
        </p>
        {m.username && m.display_name && (
          <p className="text-sm text-muted">@{m.username}</p>
        )}
      </div>
      <Badge
        tone={
          m.role === "owner"
            ? "accent"
            : m.role === "moderator"
              ? "sun"
              : "neutral"
        }
      >
        {m.role}
      </Badge>
      {canManage && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <IconButton
              aria-label="actions"
              variant="ghost"
              size="sm"
              disabled={busy}
              aria-busy={busy || undefined}
              className="min-h-11 min-w-11"
            >
              <MoreVertical className="size-[18px]" aria-hidden="true" />
            </IconButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {m.role === "member" && canManage && (
              <DropdownMenuItem onSelect={() => onPromote?.("moderator")}>
                Promote to moderator
              </DropdownMenuItem>
            )}
            {m.role === "moderator" && canPromoteToOwner && (
              <DropdownMenuItem onSelect={() => onPromote?.("owner")}>
                Promote to owner
              </DropdownMenuItem>
            )}
            {m.role === "moderator" && canManage && (
              <DropdownMenuItem onSelect={() => onDemote?.("moderator")}>
                Demote to member
              </DropdownMenuItem>
            )}
            {m.role === "owner" && canDemoteOwner && (
              <DropdownMenuItem onSelect={() => onDemote?.("moderator")}>
                Demote to moderator
              </DropdownMenuItem>
            )}
            {m.role === "owner" && isOnlyOwner && (
              <DropdownMenuItem disabled title="At least one owner required">
                Demote to moderator
              </DropdownMenuItem>
            )}
            {(canPromote || canDemote || canDemoteOwner) && (
              <DropdownMenuSeparator />
            )}
            <DropdownMenuItem
              variant="destructive"
              disabled={isOnlyOwner && m.role === "owner"}
              title={
                isOnlyOwner && m.role === "owner"
                  ? "At least one owner required"
                  : undefined
              }
              onSelect={async () => {
                const ok = await confirm({
                  title: "Remove member?",
                  message: "Remove this member from the group?",
                  confirmLabel: "Remove",
                  tone: "danger",
                });
                if (ok) onRemove?.();
              }}
            >
              Remove from group
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}

export function MembersList({
  slug,
  canManage,
  viewerRole,
  onAdd,
}: MembersListProps) {
  const { data, isLoading, error } = useSubgroupMembers(slug);
  const remove = useRemoveMember(slug);
  const changeRole = useChangeRole(slug);

  return (
    <div className="flex flex-col gap-2">
      {canManage && (
        <div className="flex justify-end">
          <Button size="sm" className="min-h-11" onClick={onAdd}>
            Add member
          </Button>
        </div>
      )}
      {isLoading && (
        <div className="flex flex-col gap-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={48} />
          ))}
        </div>
      )}
      {error && (
        <EmptyState title="Couldn't load members" description={String(error)} />
      )}
      {data && data.length === 0 && <EmptyState title="No members yet" />}
      {data?.map((m) => (
        <MemberRow
          key={m.user_id}
          m={m}
          members={data || []}
          canManage={canManage}
          viewerRole={viewerRole}
          busy={remove.isPending || changeRole.isPending}
          onRemove={() => remove.mutate(m.user_id)}
          onPromote={(role) =>
            changeRole.mutateAsync({ user_id: m.user_id, role }).catch(() => {
              /* toast on error handled by hook */
            })
          }
          onDemote={(role) =>
            changeRole.mutateAsync({ user_id: m.user_id, role }).catch(() => {
              /* toast on error handled by hook */
            })
          }
        />
      ))}
    </div>
  );
}

export default MembersList;
