'use client';
/**
 * @file components/layout/MobileNav.tsx
 * @brief Fixed bottom nav for mobile. Three primary destinations + More.
 *        "More" toggles the full-screen drawer that exposes the rest.
 */
import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import Box from '@mui/joy/Box';
import Sheet from '@mui/joy/Sheet';
import Typography from '@mui/joy/Typography';
import { EllipsisHorizontalIcon } from '@heroicons/react/24/outline';
import { Drawer } from '@/components/ui/Drawer';
import { NAV_ITEMS, isNavActive, type IconType, type NavItem } from './navItems';

const MOBILE = NAV_ITEMS.filter((i) => i.mobile);
const OVERFLOW = NAV_ITEMS.filter((i) => !i.mobile);

function NavTile({
  href,
  label,
  Icon,
  active,
  onClick,
}: {
  href?: string;
  label: string;
  Icon: IconType;
  active?: boolean;
  onClick?: () => void;
}) {
  const inner = (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 0.25,
        py: 1,
        color: active ? 'primary.plainColor' : 'text.secondary',
        fontSize: '0.7rem',
      }}
    >
      <Icon aria-hidden width={22} height={22} />
      <span>{label}</span>
    </Box>
  );
  return href ? (
    <Box component={Link} href={href} sx={{ flex: 1 }}>
      {inner}
    </Box>
  ) : (
    <Box
      component="button"
      type="button"
      onClick={onClick}
      sx={{ flex: 1, all: 'unset', cursor: 'pointer' }}
    >
      {inner}
    </Box>
  );
}

export function MobileNav() {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);

  return (
    <>
      <Sheet
        variant="outlined"
        sx={{
          display: { xs: 'flex', md: 'none' },
          position: 'sticky',
          bottom: 0,
          zIndex: 100,
          borderLeft: 0,
          borderRight: 0,
          borderBottom: 0,
        }}
      >
        <Box sx={{ display: 'flex', width: '100%' }}>
          {MOBILE.map((i: NavItem) => (
            <NavTile
              key={i.href}
              href={i.href}
              label={i.label}
              Icon={i.Icon}
              active={isNavActive(pathname, i.href)}
            />
          ))}
          <Box
            component="button"
            type="button"
            aria-expanded={moreOpen}
            aria-controls="more-nav"
            onClick={() => setMoreOpen(!moreOpen)}
            sx={{ flex: 1, all: 'unset', cursor: 'pointer' }}
          >
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 0.25,
                py: 1,
                color: 'text.secondary',
                fontSize: '0.7rem',
              }}
            >
              <EllipsisHorizontalIcon aria-hidden width={22} height={22} />
              <span>More</span>
            </Box>
          </Box>
        </Box>
      </Sheet>

      <Drawer
        id="more-nav"
        side="bottom"
        open={moreOpen}
        onClose={() => setMoreOpen(false)}
        aria-label="More navigation"
      >
        <Box sx={{ p: 2 }}>
          <Typography level="title-md" sx={{ mb: 1, fontFamily: 'var(--font-display)' }}>
            More
          </Typography>
          <Box component="ul" sx={{ listStyle: 'none', p: 0, m: 0 }}>
            {OVERFLOW.map((i) => {
              const { Icon } = i;
              return (
                <Box component="li" key={i.href}>
                  <Box
                    component={Link}
                    href={i.href}
                    onClick={() => setMoreOpen(false)}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1.5,
                      px: 2,
                      py: 1.5,
                      borderRadius: 'md',
                      '&:hover': { background: 'neutral.softBg' },
                    }}
                  >
                    <Icon aria-hidden width={22} height={22} />
                    <span>{i.label}</span>
                  </Box>
                </Box>
              );
            })}
          </Box>
        </Box>
      </Drawer>
    </>
  );
}
