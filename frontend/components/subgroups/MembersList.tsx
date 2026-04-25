'use client';
/**
 * @file components/subgroups/MembersList.tsx
 * @brief List subgroup members with role pills + admin actions.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import Box from '@mui/joy/Box';
import Typography from '@mui/joy/Typography';
import { Avatar, Chip, Button, IconButton, Skeleton, EmptyState } from '@/components/ui';
import { TrashIcon } from '@heroicons/react/24/outline';
import { useSubgroupMembers, useRemoveMember } from '@/hooks/useSubgroups';
import type { Membership } from '@/lib/api/subgroups';

export interface MembersListProps {
  slug: string;
  canManage?: boolean;
  onAdd?: () => void;
}

function MemberRow({
  m,
  canManage,
  onRemove,
  busy,
}: {
  m: Membership;
  canManage?: boolean;
  onRemove?: () => void;
  busy?: boolean;
}) {
  return (
    <Stack
      direction="row"
      alignItems="center"
      spacing={1.5}
      sx={{ py: 1, borderBottom: '1px solid', borderColor: 'divider' }}
    >
      <Avatar src={m.avatar_url ?? undefined} alt={m.display_name ?? m.username ?? ''} />
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography level="body-md">{m.display_name ?? m.username ?? m.user_id}</Typography>
        {m.username && m.display_name && (
          <Typography level="body-xs" sx={{ color: 'text.tertiary' }}>
            @{m.username}
          </Typography>
        )}
      </Box>
      <Chip
        size="sm"
        color={m.role === 'owner' ? 'primary' : m.role === 'moderator' ? 'warning' : 'neutral'}
      >
        {m.role}
      </Chip>
      {canManage && m.role !== 'owner' && (
        <IconButton
          aria-label="Remove member"
          variant="plain"
          color="danger"
          size="sm"
          loading={busy}
          onClick={onRemove}
        >
          <TrashIcon width={18} height={18} />
        </IconButton>
      )}
    </Stack>
  );
}

export function MembersList({ slug, canManage, onAdd }: MembersListProps) {
  const { data, isLoading, error } = useSubgroupMembers(slug);
  const remove = useRemoveMember(slug);

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
      {error && <EmptyState title="Couldn't load members" description={String(error)} />}
      {data && data.length === 0 && <EmptyState title="No members yet" />}
      {data?.map((m) => (
        <MemberRow
          key={m.user_id}
          m={m}
          canManage={canManage}
          busy={remove.isPending && remove.variables === m.user_id}
          onRemove={() => remove.mutate(m.user_id)}
        />
      ))}
    </Stack>
  );
}

export default MembersList;
