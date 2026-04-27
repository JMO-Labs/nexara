'use client';
/**
 * @file components/layout/TopBar.tsx
 * @brief Sticky top bar. Brand mark, command palette trigger (⌘K),
 *        notifications bell, avatar dropdown. The palette itself owns
 *        its open state and ⌘K listener (see CommandPalette).
 */
import Link from 'next/link';
import Box from '@mui/joy/Box';
import Sheet from '@mui/joy/Sheet';
import Typography from '@mui/joy/Typography';
import Stack from '@mui/joy/Stack';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { IconButton } from '@/components/ui/IconButton';
import { NotificationsBell } from '@/components/notifications/NotificationsBell';
import { AvatarMenu } from './AvatarMenu';
import { useUI } from '@/stores/ui';

export function TopBar() {
  const openPalette = useUI((s) => s.setCommandPaletteOpen);
  return (
    <Sheet
      component="header"
      variant="outlined"
      sx={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        px: { xs: 2, md: 3 },
        py: 1,
        borderLeft: 0,
        borderRight: 0,
        borderTop: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 2,
      }}
    >
      <Box component={Link} href="/app" sx={{ display: 'flex', alignItems: 'center' }}>
        <Typography
          level="title-md"
          sx={{ fontFamily: 'var(--font-display)', letterSpacing: '0.02em' }}
        >
          Nexara
        </Typography>
      </Box>
      <Box sx={{ flex: 1 }}>
        <Box
          component="button"
          type="button"
          onClick={() => openPalette(true)}
          aria-label="Open command palette"
          data-tour="topbar-search"
          sx={{
            all: 'unset',
            cursor: 'pointer',
            display: { xs: 'none', sm: 'flex' },
            alignItems: 'center',
            gap: 1,
            maxWidth: 480,
            width: '100%',
            px: 1.5,
            py: 0.75,
            borderRadius: 'md',
            border: '1px solid',
            borderColor: 'neutral.outlinedBorder',
            color: 'text.tertiary',
            fontSize: '0.85rem',
            '&:hover': { background: 'neutral.softBg' },
          }}
        >
          <MagnifyingGlassIcon aria-hidden width={16} height={16} />
          <span>Search Nexara…</span>
          <span style={{ marginLeft: 'auto', opacity: 0.6 }}>⌘K</span>
        </Box>
      </Box>
      <Stack direction="row" spacing={1} alignItems="center">
        <Box sx={{ display: { sm: 'none' } }}>
          <IconButton
            tooltip="Search"
            shortcut="Ctrl+K"
            variant="plain"
            color="neutral"
            aria-label="Search"
            onClick={() => openPalette(true)}
          >
            <MagnifyingGlassIcon aria-hidden width={20} height={20} />
          </IconButton>
        </Box>
        <NotificationsBell />
        <AvatarMenu />
      </Stack>
    </Sheet>
  );
}
