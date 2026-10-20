"use client";
/**
 * @file components/subgroups/MembersList.tsx
 * @brief List subgroup members with role pills + admin actions.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import Box from "@mui/joy/Box";
import Typography from "@mui/joy/Typography";
import Menu from "@mui/joy/Menu";
import MenuItem from "@mui/joy/MenuItem";
import MenuButton from "@mui/joy/MenuButton";
import Dropdown from "@mui/joy/Dropdown";
import Divider from "@mui/joy/Divider";
import {
  Avatar,
  Chip,
  Button,
  IconButton,
  Skeleton,
  EmptyState,
} from "@/components/ui";
import { EllipsisVerticalIcon } from "@heroicons/react/24/outline";
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
    <Stack
      direction="row"
      alignItems="center"
      spacing={1.5}
      sx={{ py: 1, borderBottom: "1px solid", borderColor: "divider" }}
    >
      <Avatar
        src={m.avatar_url ?? undefined}
        alt={m.display_name ?? m.username ?? ""}
      />
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography level="body-md">
          {m.display_name ?? m.username ?? m.user_id}
        </Typography>
        {m.username && m.display_name && (
          <Typography level="body-xs" sx={{ color: "text.tertiary" }}>
            @{m.username}
          </Typography>
        )}
      </Box>
      <Chip
        size="sm"
        color={
          m.role === "owner"
            ? "primary"
            : m.role === "moderator"
              ? "warning"
              : "neutral"
        }
      >
        {m.role}
      </Chip>
      {canManage && (canPromote || canDemote || canDemoteOwner || true) && (
        <Dropdown>
          <MenuButton
            slots={{ root: IconButton }}
            aria-label="actions"
            variant="plain"
            color="neutral"
            size="sm"
            loading={busy}
          >
            <EllipsisVerticalIcon width={18} height={18} />
          </MenuButton>
          <Menu placement="bottom-end" size="sm">
            {m.role === "member" && canManage && (
              <MenuItem onClick={() => onPromote?.("moderator")}>
                Promote to moderator
              </MenuItem>
            )}
            {m.role === "moderator" && canPromoteToOwner && (
              <MenuItem onClick={() => onPromote?.("owner")}>
                Promote to owner
              </MenuItem>
            )}
            {m.role === "moderator" && canManage && (
              <MenuItem onClick={() => onDemote?.("moderator")}>
                Demote to member
              </MenuItem>
            )}
            {m.role === "owner" && canDemoteOwner && (
              <MenuItem onClick={() => onDemote?.("moderator")}>
                Demote to moderator
              </MenuItem>
            )}
            {m.role === "owner" && isOnlyOwner && (
              <MenuItem
                disabled
                aria-disabled="true"
                title="At least one owner required"
              >
                Demote to moderator
              </MenuItem>
            )}
            {(canPromote || canDemote || canDemoteOwner) && <Divider />}
            <MenuItem
              color="danger"
              disabled={isOnlyOwner && m.role === "owner"}
              aria-disabled={isOnlyOwner && m.role === "owner"}
              title={
                isOnlyOwner && m.role === "owner"
                  ? "At least one owner required"
                  : ""
              }
              onClick={async () => {
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
            </MenuItem>
          </Menu>
        </Dropdown>
      )}
    </Stack>
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
    <Stack spacing={1}>
      {canManage && (
        <Stack direction="row" justifyContent="flex-end">
          <Button size="sm" onClick={onAdd}>
            Add member
          </Button>
        </Stack>
      )}
      {isLoading && (
        <Stack spacing={1}>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={48} />
          ))}
        </Stack>
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
    </Stack>
  );
}

export default MembersList;
