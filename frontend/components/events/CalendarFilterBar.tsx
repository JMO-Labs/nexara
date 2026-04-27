'use client';
/**
 * @file components/events/CalendarFilterBar.tsx
 * @brief Toolbar above the events calendar: month wordmark + nav, "Today",
 *        scope toggle (all / community / specific subgroup), and a "New event"
 *        action. The scope chips reuse per-subgroup colors so the filter row
 *        echoes the calendar bars themselves.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { addMonths, format, subMonths } from 'date-fns';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { Button, IconButton } from '@/components/ui';
import { toneForSubgroupId } from './eventColors';
import type { Subgroup } from '@/lib/api/subgroups';

export type Scope = { kind: 'all' } | { kind: 'community' } | { kind: 'subgroup'; id: string };

export interface CalendarFilterBarProps {
  month: Date;
  onMonthChange: (m: Date) => void;
  scope: Scope;
  onScopeChange: (s: Scope) => void;
  subgroups: Subgroup[];
  onCreate: () => void;
}

function scopeMatches(a: Scope, b: Scope): boolean {
  if (a.kind !== b.kind) return false;
  if (a.kind === 'subgroup' && b.kind === 'subgroup') return a.id === b.id;
  return true;
}

function ScopeChip({
  active,
  color,
  onClick,
  children,
}: {
  active: boolean;
  color: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <Box
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 0.75,
        px: 1.25,
        py: 0.5,
        borderRadius: '999px',
        border: '1px solid',
        borderColor: active ? color : 'divider',
        backgroundColor: active ? color : 'transparent',
        color: active ? '#fff' : 'text.primary',
        cursor: 'pointer',
        fontSize: 12,
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        transition: 'all 120ms ease',
        '&:hover': { borderColor: color },
        '&:focus-visible': {
          outline: '2px solid',
          outlineColor: color,
          outlineOffset: '2px',
        },
      }}
    >
      <Box
        sx={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          backgroundColor: active ? '#fff' : color,
        }}
      />
      {children}
    </Box>
  );
}

export function CalendarFilterBar({
  month,
  onMonthChange,
  scope,
  onScopeChange,
  subgroups,
  onCreate,
}: CalendarFilterBarProps) {
  return (
    <Stack spacing={2} sx={{ mb: 3 }}>
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        alignItems={{ xs: 'flex-start', md: 'flex-end' }}
        justifyContent="space-between"
        spacing={2}
      >
        <Box>
          <Typography
            level="body-xs"
            textColor="text.tertiary"
            sx={{
              textTransform: 'uppercase',
              letterSpacing: '0.18em',
              fontWeight: 700,
              mb: 0.25,
            }}
          >
            Calendar · {format(month, 'yyyy')}
          </Typography>
          <Typography
            level="h1"
            component="h1"
            sx={{
              fontFamily: 'var(--font-display)',
              fontSize: { xs: '2.4rem', md: '3.2rem' },
              lineHeight: 1,
              letterSpacing: '-0.02em',
            }}
          >
            {format(month, 'MMMM')}
          </Typography>
        </Box>

        <Stack direction="row" spacing={1} alignItems="center">
          <IconButton
            variant="outlined"
            size="sm"
            aria-label="Previous month"
            onClick={() => onMonthChange(subMonths(month, 1))}
          >
            <ChevronLeftIcon width={16} />
          </IconButton>
          <Button
            variant="outlined"
            size="sm"
            onClick={() => onMonthChange(new Date())}
          >
            Today
          </Button>
          <IconButton
            variant="outlined"
            size="sm"
            aria-label="Next month"
            onClick={() => onMonthChange(addMonths(month, 1))}
          >
            <ChevronRightIcon width={16} />
          </IconButton>
          <Box sx={{ width: 8 }} />
          <Button onClick={onCreate}>New event</Button>
        </Stack>
      </Stack>

      <Stack
        direction="row"
        spacing={1}
        sx={{
          flexWrap: 'wrap',
          rowGap: 1,
          alignItems: 'center',
        }}
      >
        <Typography
          level="body-xs"
          textColor="text.tertiary"
          sx={{
            textTransform: 'uppercase',
            letterSpacing: '0.14em',
            fontWeight: 600,
            mr: 0.5,
          }}
        >
          Calendars
        </Typography>
        <ScopeChip
          active={scope.kind === 'all'}
          color="var(--joy-palette-neutral-solidBg, #1f2937)"
          onClick={() => onScopeChange({ kind: 'all' })}
        >
          All
        </ScopeChip>
        <ScopeChip
          active={scope.kind === 'community'}
          color={toneForSubgroupId(null).solid}
          onClick={() => onScopeChange({ kind: 'community' })}
        >
          Community
        </ScopeChip>
        {subgroups.map((sg) => {
          const tone = toneForSubgroupId(sg.id);
          const active = scopeMatches(scope, { kind: 'subgroup', id: sg.id });
          return (
            <ScopeChip
              key={sg.id}
              active={active}
              color={tone.solid}
              onClick={() => onScopeChange({ kind: 'subgroup', id: sg.id })}
            >
              {sg.name}
            </ScopeChip>
          );
        })}
      </Stack>
    </Stack>
  );
}

export default CalendarFilterBar;
