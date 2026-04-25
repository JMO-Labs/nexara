'use client';
/**
 * @file components/chat/NewDmModal.tsx
 * @brief User-picker modal that lists community members, filters by query,
 *        and opens (or creates) a DM channel on selection.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Box from '@mui/joy/Box';
import { Modal, Input, Avatar, Skeleton } from '@/components/ui';
import { useQuery } from '@tanstack/react-query';
import { listUsers, type UserSummary } from '@/lib/api/users';

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
  const [q, setQ] = React.useState('');

  const usersQ = useQuery({
    queryKey: ['users', 'list', 'all'],
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
    setQ('');
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="New direct message">
      <Stack spacing={1.5} sx={{ width: { xs: '100%', sm: 420 } }}>
        <Input
          autoFocus
          placeholder="Search by name or @username"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <Box sx={{ maxHeight: 360, overflowY: 'auto', mx: -1 }}>
          {usersQ.isLoading ? (
            <Stack spacing={1} px={1}>
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} height={48} />
              ))}
            </Stack>
          ) : filtered.length === 0 ? (
            <Typography
              level="body-sm"
              textColor="text.tertiary"
              sx={{ p: 2, textAlign: 'center' }}
            >
              No matching users.
            </Typography>
          ) : (
            <Stack>
              {filtered.map((u) => (
                <Box
                  key={u.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => select(u)}
                  onKeyDown={(e) =>
                    (e.key === 'Enter' || e.key === ' ') && select(u)
                  }
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1.5,
                    px: 2,
                    py: 1,
                    cursor: 'pointer',
                    borderRadius: 'sm',
                    '&:hover': { bgcolor: 'background.level1' },
                    outline: 'none',
                    '&:focus-visible': { boxShadow: 'sm' },
                  }}
                >
                  <Avatar size="sm" src={u.avatar_url ?? undefined}>
                    {u.display_name.charAt(0)}
                  </Avatar>
                  <Stack sx={{ minWidth: 0 }}>
                    <Typography level="title-sm" noWrap>
                      {u.display_name}
                    </Typography>
                    <Typography level="body-xs" textColor="text.tertiary" noWrap>
                      @{u.username}
                    </Typography>
                  </Stack>
                </Box>
              ))}
            </Stack>
          )}
        </Box>
      </Stack>
    </Modal>
  );
}
