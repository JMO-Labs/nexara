'use client';
/**
 * @file components/notifications/NotificationsBell.tsx
 * @brief Top-bar bell. Shows unread badge, opens a popover with the
 *        recent notifications list. Stream-driven: SSE updates the count
 *        and prepends new items live.
 */
import { useState, useEffect, useRef } from 'react';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Sheet from '@mui/joy/Sheet';
import Badge from '@mui/joy/Badge';
import Modal from '@mui/joy/Modal';
import ModalClose from '@mui/joy/ModalClose';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { BellIcon } from '@heroicons/react/24/outline';
import { IconButton } from '@/components/ui/IconButton';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  getUnreadCount,
  listNotifications,
  markAllRead,
  STREAM_PATH,
  type NotificationItem,
} from '@/lib/api/notifications';
import { useSSE } from '@/hooks/useSSE';
import { useSession } from '@/stores/session';

const COUNT_KEY = ['notifications', 'unread-count'] as const;
const LIST_KEY = ['notifications', 'list'] as const;

export function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [pulse, setPulse] = useState(false);
  const [badgeKey, setBadgeKey] = useState(0);
  const prevCountRef = useRef(0);
  const debounceTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const isAuthed = useSession((s) => s.status === 'authenticated');
  const qc = useQueryClient();

  const { data: count } = useQuery({
    queryKey: COUNT_KEY,
    queryFn: getUnreadCount,
    enabled: isAuthed,
    staleTime: 30_000,
  });

  const { data: list, isLoading } = useQuery({
    queryKey: LIST_KEY,
    queryFn: () => listNotifications(),
    enabled: isAuthed && open,
  });

  const markAll = useMutation({
    mutationFn: markAllRead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: COUNT_KEY });
      qc.invalidateQueries({ queryKey: LIST_KEY });
    },
  });

  useSSE(STREAM_PATH, {
    enabled: isAuthed,
    onMessage: (payload) => {
      // Backend pushes notification events on the same stream. Any inbound
      // event invalidates the count; if the list is open, refresh it too.
      qc.invalidateQueries({ queryKey: COUNT_KEY });
      if (open) qc.invalidateQueries({ queryKey: LIST_KEY });
      void payload;
    },
  });

  const unread = count?.count ?? 0;

  // Debounced pulse on count change
  useEffect(() => {
    if (unread > prevCountRef.current && unread > 0) {
      if (debounceTimeoutRef.current) clearTimeout(debounceTimeoutRef.current);
      setPulse(true);
      setBadgeKey((k) => k + 1);

      debounceTimeoutRef.current = setTimeout(() => {
        setPulse(false);
      }, 1000);
    }
    prevCountRef.current = unread;

    return () => {
      if (debounceTimeoutRef.current) clearTimeout(debounceTimeoutRef.current);
    };
  }, [unread]);

  return (
    <>
      <Badge
        key={`badge-${badgeKey}`}
        badgeContent={unread > 99 ? '99+' : unread}
        color="danger"
        invisible={unread === 0}
        size="sm"
      >
        <motion.div
          animate={pulse ? { rotate: [0, 8, -8, 0] } : { rotate: 0 }}
          transition={{ duration: 0.35, ease: 'easeInOut' }}
        >
          <IconButton
            tooltip="Notifications"
            variant="plain"
            color="neutral"
            aria-label={
              unread > 0 ? `Notifications, ${unread} unread` : 'Notifications'
            }
            onClick={() => setOpen(true)}
            data-tour="bell"
          >
            <BellIcon aria-hidden width={20} height={20} />
          </IconButton>
        </motion.div>
      </Badge>

      <Modal open={open} onClose={() => setOpen(false)}>
        <Sheet
          variant="outlined"
          sx={{
            position: 'absolute',
            top: 64,
            right: 16,
            left: { xs: 16, sm: 'auto' },
            width: { xs: 'auto', sm: 380 },
            maxHeight: 'calc(100dvh - 96px)',
            borderRadius: 'lg',
            boxShadow: 'lg',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}
          >
            <Typography level="title-md" sx={{ fontFamily: 'var(--font-display)' }}>
              Notifications
            </Typography>
            <Stack direction="row" spacing={1} alignItems="center">
              {unread > 0 && (
                <Button
                  size="sm"
                  variant="plain"
                  onClick={() => markAll.mutate()}
                  loading={markAll.isPending}
                >
                  Mark all read
                </Button>
              )}
              <ModalClose variant="plain" sx={{ position: 'static' }} />
            </Stack>
          </Stack>
          <Box sx={{ overflow: 'auto', flex: 1 }}>
            {isLoading && (
              <Stack spacing={1} sx={{ p: 2 }}>
                <Skeleton height={48} rounded="md" />
                <Skeleton height={48} rounded="md" />
                <Skeleton height={48} rounded="md" />
              </Stack>
            )}
            {!isLoading && (list?.items.length ?? 0) === 0 && (
              <Typography
                level="body-sm"
                color="neutral"
                sx={{ p: 4, textAlign: 'center' }}
              >
                You&rsquo;re all caught up.
              </Typography>
            )}
            {!isLoading && list?.items.map((n) => <Row key={n.id} item={n} />)}
          </Box>
        </Sheet>
      </Modal>
    </>
  );
}

function Row({ item }: { item: NotificationItem }) {
  const unread = !item.read_at;
  const Inner = (
    <Box
      sx={{
        px: 2,
        py: 1.5,
        borderBottom: '1px solid',
        borderColor: 'divider',
        background: unread ? 'primary.softBg' : 'transparent',
        '&:hover': { background: 'neutral.softBg' },
      }}
    >
      <Typography level="title-sm">{item.title}</Typography>
      {item.body && (
        <Typography level="body-sm" color="neutral">
          {item.body}
        </Typography>
      )}
      <Typography level="body-xs" color="neutral" sx={{ mt: 0.5 }}>
        {formatTime(item.created_at)}
      </Typography>
    </Box>
  );
  return item.link ? (
    <Box component={Link} href={item.link} sx={{ display: 'block' }}>
      {Inner}
    </Box>
  ) : (
    Inner
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86_400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString();
}
