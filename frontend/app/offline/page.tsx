/**
 * @file app/offline/page.tsx
 * @brief Offline fallback served by the service worker when navigation
 *        fetches fail. Static so it can be precached at install.
 */
import Link from 'next/link';
import Box from '@mui/joy/Box';
import Typography from '@mui/joy/Typography';
import Button from '@mui/joy/Button';

export const dynamic = 'force-static';

export const metadata = {
  title: 'Offline',
};

export default function OfflinePage() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
        p: 4,
        textAlign: 'center',
      }}
    >
      <Typography level="h1" fontFamily="var(--font-fraunces)">
        You&rsquo;re offline
      </Typography>
      <Typography level="body-md" sx={{ maxWidth: 420 }}>
        Nexara can&rsquo;t reach the network right now. Check your connection
        and try again.
      </Typography>
      <Link href="/app" prefetch={false}>
        <Button variant="solid" color="primary">Retry</Button>
      </Link>
    </Box>
  );
}
