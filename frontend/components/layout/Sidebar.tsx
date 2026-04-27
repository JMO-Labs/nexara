'use client';
/**
 * @file components/layout/Sidebar.tsx
 * @brief 240px left rail. Hides under md breakpoint (mobile uses MobileNav).
 */
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Sheet from '@mui/joy/Sheet';
import { NAV_ITEMS } from './navItems';

export function Sidebar() {
  const pathname = usePathname();
  return (
    <Sheet
      component="nav"
      aria-label="Primary"
      variant="outlined"
      sx={{
        display: { xs: 'none', md: 'flex' },
        flexDirection: 'column',
        width: 240,
        borderTop: 0,
        borderBottom: 0,
        borderLeft: 0,
        p: 2,
        gap: 0.5,
      }}
    >
      <Typography
        level="title-sm"
        sx={{
          px: 2,
          pb: 1,
          fontFamily: 'var(--font-display)',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: 'text.tertiary',
        }}
      >
        Nexara
      </Typography>
      <Stack
        spacing={0.25}
        component="ul"
        sx={{ listStyle: 'none', m: 0, p: 0 }}
        data-tour="sidebar-nav"
      >
        {NAV_ITEMS.map((item) => {
          const active = pathname.startsWith(item.href);
          const { Icon } = item;
          return (
            <Box component="li" key={item.href}>
              <Box
                component={Link}
                href={item.href}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  px: 2,
                  py: 1.25,
                  borderRadius: 'md',
                  color: active ? 'primary.plainColor' : 'text.primary',
                  background: active ? 'primary.softBg' : 'transparent',
                  fontWeight: active ? 600 : 500,
                  '&:hover': { background: 'neutral.softBg' },
                }}
              >
                <Icon aria-hidden width={20} height={20} />
                <span>{item.label}</span>
              </Box>
            </Box>
          );
        })}
      </Stack>
    </Sheet>
  );
}
