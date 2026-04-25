'use client';
/**
 * @file components/subgroups/SubgroupCard.tsx
 * @brief Tile rendering a subgroup summary; click selects, button joins.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Card, Button, Chip, Avatar } from '@/components/ui';
import type { Subgroup } from '@/lib/api/subgroups';

export interface SubgroupCardProps {
  subgroup: Subgroup;
  memberCount?: number;
  isMember?: boolean;
  onSelect: (slug: string) => void;
  onJoin?: (slug: string) => void;
  onLeave?: (slug: string) => void;
  busy?: boolean;
}

export function SubgroupCard({
  subgroup,
  memberCount,
  isMember,
  onSelect,
  onJoin,
  onLeave,
  busy,
}: SubgroupCardProps) {
  const handleClick = () => onSelect(subgroup.slug);
  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
      sx={{ cursor: 'pointer', '&:hover': { borderColor: 'primary.outlinedBorder' } }}
    >
      <Stack direction="row" spacing={2} alignItems="center">
        <Avatar src={subgroup.avatar_url ?? undefined} alt={subgroup.name} />
        <Stack sx={{ flex: 1, minWidth: 0 }}>
          <Typography level="title-md" sx={{ fontFamily: 'var(--font-display)' }}>
            {subgroup.name}
          </Typography>
          {subgroup.description && (
            <Typography level="body-sm" sx={{ color: 'text.tertiary' }} noWrap>
              {subgroup.description}
            </Typography>
          )}
          <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
            {subgroup.is_private && <Chip color="warning" size="sm">Private</Chip>}
            <Chip color="neutral" size="sm">{subgroup.join_policy.replace('_', ' ')}</Chip>
            {typeof memberCount === 'number' && (
              <Typography level="body-xs" sx={{ color: 'text.tertiary' }}>
                {memberCount} {memberCount === 1 ? 'member' : 'members'}
              </Typography>
            )}
          </Stack>
        </Stack>
        {isMember ? (
          <Button
            variant="outlined"
            color="neutral"
            size="sm"
            loading={busy}
            onClick={(e) => {
              e.stopPropagation();
              onLeave?.(subgroup.slug);
            }}
          >
            Leave
          </Button>
        ) : (
          <Button
            size="sm"
            loading={busy}
            onClick={(e) => {
              e.stopPropagation();
              onJoin?.(subgroup.slug);
            }}
          >
            Join
          </Button>
        )}
      </Stack>
    </Card>
  );
}

export default SubgroupCard;
