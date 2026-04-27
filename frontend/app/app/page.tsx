'use client';
/**
 * @file app/app/page.tsx
 * @brief Dashboard. Two-column layout: feed (primary) + calendar rail.
 *        Calendar collapses below feed under lg breakpoint.
 */
import Box from '@mui/joy/Box';
import Typography from '@mui/joy/Typography';
import { FeedView } from '@/components/feed/FeedView';
import { CalendarRail } from '@/components/events/CalendarRail';
import { useSession } from '@/stores/session';

export default function AppHome() {
  const user = useSession((s) => s.user);
  return (
    <Box
      sx={{
        display: 'grid',
        gap: { xs: 2, lg: 3 },
        width: '100%',
        flex: 1,
        gridTemplateColumns: { xs: '1fr', lg: 'minmax(0, 720px) minmax(0, 1fr)' },
        alignItems: 'stretch',
      }}
    >
      <Box sx={{ minWidth: 0, width: '100%' }}>
        <FeedView
          heading={
            <Typography level="h2" sx={{ fontFamily: 'var(--font-display)' }}>
              Welcome back{user?.display_name ? `, ${user.display_name}` : ''}.
            </Typography>
          }
        />
      </Box>
      <Box sx={{ minWidth: 0, width: '100%' }}>
        <CalendarRail />
      </Box>
    </Box>
  );
}
