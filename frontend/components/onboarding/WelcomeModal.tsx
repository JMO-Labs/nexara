/**
 * @file WelcomeModal.tsx
 * @brief Pre-tour welcome screen with quick action links.
 *
 * Shown before onboarding tour starts for first-time users.
 * Provides direct shortcuts to common first actions.
 */

'use client';

import Link from 'next/link';
import Modal from '@mui/joy/Modal';
import ModalClose from '@mui/joy/ModalClose';
import Sheet from '@mui/joy/Sheet';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Button from '@mui/joy/Button';
import Box from '@mui/joy/Box';
import {
  UserCircleIcon,
  UserGroupIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline';
import { useSession } from '@/stores/session';
import { useState } from 'react';
import * as usersApi from '@/lib/api/users';

interface ActionLink {
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  label: string;
  href: string;
  description: string;
}

const ACTIONS: ActionLink[] = [
  {
    icon: UserCircleIcon,
    label: 'Edit profile',
    href: '/app/settings?tab=profile',
    description: 'Complete your profile info',
  },
  {
    icon: UserGroupIcon,
    label: 'Find friends',
    href: '/app/members',
    description: 'Connect with community members',
  },
  {
    icon: CalendarIcon,
    label: 'Browse events',
    href: '/app/events',
    description: 'Discover upcoming events',
  },
];

export function WelcomeModal() {
  const user = useSession((s) => s.user);
  const [isOpen, setIsOpen] = useState(true);

  // Only show if user is authenticated and hasn't completed onboarding
  const shouldShow = !!user && !user.tour_completed_at;

  const handleSkip = async () => {
    setIsOpen(false);
    await usersApi.completeOnboarding();
  };

  if (!shouldShow) return null;

  return (
    <Modal open={isOpen} onClose={() => setIsOpen(false)} sx={{ zIndex: 1300 }}>
      <Sheet
        variant="outlined"
        sx={{
          p: 3,
          borderRadius: 'md',
          maxWidth: 500,
          mx: 'auto',
        }}
      >
        <ModalClose variant="plain" sx={{ m: 1 }} />
        <Stack spacing={3}>
          <Box>
            <Typography level="h2" component="h1" sx={{ mb: 0.5 }}>
              Welcome to the community!
            </Typography>
            <Typography level="body-md" textColor="text.tertiary">
              Let&apos;s help you get started with a quick tour and some useful links.
            </Typography>
          </Box>

          <Stack spacing={1.5}>
            {ACTIONS.map((action) => {
              const Icon = action.icon;
              return (
                <Link key={action.href} href={action.href} style={{ textDecoration: 'none' }}>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1.5,
                      p: 1.5,
                      borderRadius: 'md',
                      border: '1px solid',
                      borderColor: 'divider',
                      transition: 'all 0.2s ease',
                      cursor: 'pointer',
                      '&:hover': {
                        borderColor: 'primary.main',
                        backgroundColor: 'primary.softBg',
                      },
                    }}
                  >
                    <Icon width={24} height={24} style={{ flex: 0 }} />
                    <Box sx={{ flex: 1 }}>
                      <Typography level="body-sm" fontWeight="md">
                        {action.label}
                      </Typography>
                      <Typography level="body-xs" textColor="text.tertiary">
                        {action.description}
                      </Typography>
                    </Box>
                  </Box>
                </Link>
              );
            })}
          </Stack>

          <Stack direction="row" spacing={1.5}>
            <Button
              fullWidth
              variant="plain"
              color="neutral"
              onClick={handleSkip}
            >
              Skip for now
            </Button>
            <Button
              fullWidth
              onClick={() => setIsOpen(false)}
            >
              Take tour
            </Button>
          </Stack>
        </Stack>
      </Sheet>
    </Modal>
  );
}
