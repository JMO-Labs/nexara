'use client';
/**
 * @file components/events/CalendarFilterBar.tsx
 * @brief Toolbar above the events calendar: month wordmark + nav, "Today",
 *        grouped multi-select calendar dropdown, and a "New event" action.
 *        Calendars are grouped by kind (Community, Personal, Groups) with
 *        a per-group bulk toggle and a master "All" toggle.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Dropdown from '@mui/joy/Dropdown';
import Menu from '@mui/joy/Menu';
import MenuButton from '@mui/joy/MenuButton';
import Checkbox from '@mui/joy/Checkbox';
import Divider from '@mui/joy/Divider';
import { addMonths, format, subMonths } from 'date-fns';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import { Button, IconButton } from '@/components/ui';
import { toneForSubgroupId } from './eventColors';
import type { Calendar } from '@/lib/api/calendars';

export type CalendarSourceId = string;

interface CalendarOption {
  id: CalendarSourceId;
  label: string;
  color: string;
}

interface CalendarGroup {
  kind: 'community' | 'personal' | 'subgroup';
  label: string;
  options: CalendarOption[];
}

export interface CalendarFilterBarProps {
  month: Date;
  onMonthChange: (m: Date) => void;
  selected: CalendarSourceId[];
  onSelectedChange: (ids: CalendarSourceId[]) => void;
  calendars: Calendar[];
  onCreate: () => void;
}

const GROUP_LABELS: Record<CalendarGroup['kind'], string> = {
  community: 'Community',
  personal: 'Personal',
  subgroup: 'Groups',
};

const GROUP_ORDER: CalendarGroup['kind'][] = ['community', 'personal', 'subgroup'];

function colorFor(cal: Calendar): string {
  if (cal.color) return cal.color;
  if (cal.kind === 'subgroup' && cal.subgroup_id) {
    return toneForSubgroupId(cal.subgroup_id).solid;
  }
  if (cal.kind === 'community') return toneForSubgroupId(null).solid;
  return 'var(--joy-palette-warning-solidBg, #b45309)';
}

export function buildGroups(calendars: Calendar[]): CalendarGroup[] {
  const buckets: Record<CalendarGroup['kind'], CalendarOption[]> = {
    community: [],
    personal: [],
    subgroup: [],
  };
  for (const cal of calendars) {
    buckets[cal.kind].push({ id: cal.id, label: cal.name, color: colorFor(cal) });
  }
  for (const k of GROUP_ORDER) {
    buckets[k].sort((a, b) => a.label.localeCompare(b.label));
  }
  return GROUP_ORDER
    .filter((k) => buckets[k].length > 0)
    .map((k) => ({ kind: k, label: GROUP_LABELS[k], options: buckets[k] }));
}

function summarize(selectedCount: number, total: number): string {
  if (selectedCount === 0) return 'No calendars';
  if (selectedCount === total) return 'All calendars';
  if (selectedCount === 1) return '1 calendar';
  return `${selectedCount} calendars`;
}

function Swatch({ color }: { color: string }) {
  return (
    <Box
      sx={{
        width: 10,
        height: 10,
        borderRadius: '50%',
        backgroundColor: color,
        flexShrink: 0,
      }}
    />
  );
}

export function CalendarFilterBar({
  month,
  onMonthChange,
  selected,
  onSelectedChange,
  calendars,
  onCreate,
}: CalendarFilterBarProps) {
  const groups = React.useMemo(() => buildGroups(calendars), [calendars]);
  const allOptions = React.useMemo(
    () => groups.flatMap((g) => g.options),
    [groups],
  );
  const selectedSet = React.useMemo(() => new Set(selected), [selected]);
  const allCount = allOptions.length;
  const allOn = allCount > 0 && selected.length === allCount;

  const toggleOne = (id: CalendarSourceId) => {
    if (selectedSet.has(id)) {
      onSelectedChange(selected.filter((x) => x !== id));
    } else {
      onSelectedChange([...selected, id]);
    }
  };

  const toggleAll = () => {
    if (allOn) onSelectedChange([]);
    else onSelectedChange(allOptions.map((o) => o.id));
  };

  const groupState = (g: CalendarGroup): 'all' | 'some' | 'none' => {
    const ids = g.options.map((o) => o.id);
    const on = ids.filter((id) => selectedSet.has(id)).length;
    if (on === 0) return 'none';
    if (on === ids.length) return 'all';
    return 'some';
  };

  const toggleGroup = (g: CalendarGroup) => {
    const ids = g.options.map((o) => o.id);
    const state = groupState(g);
    if (state === 'all') {
      onSelectedChange(selected.filter((x) => !ids.includes(x)));
    } else {
      const next = new Set(selected);
      ids.forEach((id) => next.add(id));
      onSelectedChange([...next]);
    }
  };

  const previewSwatches = allOptions
    .filter((o) => selectedSet.has(o.id))
    .slice(0, 4);

  const [open, setOpen] = React.useState(false);
  const triggerRef = React.useRef<HTMLButtonElement | null>(null);
  const menuRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      const target = e.target as Node | null;
      if (!target) return;
      if (menuRef.current?.contains(target)) return;
      if (triggerRef.current?.contains(target)) return;
      setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

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
        spacing={1.5}
        sx={{ flexWrap: 'wrap', rowGap: 1, alignItems: 'center' }}
      >
        <Typography
          level="body-xs"
          textColor="text.tertiary"
          sx={{
            textTransform: 'uppercase',
            letterSpacing: '0.14em',
            fontWeight: 600,
          }}
        >
          Calendars
        </Typography>

        <Dropdown open={open} onOpenChange={(_e, v) => setOpen(v)}>
          <MenuButton
            ref={triggerRef}
            variant="outlined"
            color="neutral"
            size="sm"
            endDecorator={<ChevronDownIcon width={14} />}
            sx={{
              borderRadius: '999px',
              fontSize: 12,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              gap: 1,
              color: 'text.primary',
              backgroundColor: 'background.surface',
              borderColor: 'neutral.outlinedBorder',
              '&:hover': {
                backgroundColor: 'var(--joy-palette-neutral-softHoverBg)',
                color: 'text.primary',
              },
            }}
          >
            <Stack direction="row" spacing={0.5} alignItems="center">
              {previewSwatches.map((o) => (
                <Swatch key={o.id} color={o.color} />
              ))}
            </Stack>
            <span>{summarize(selected.length, allCount)}</span>
          </MenuButton>
          <Menu
            ref={menuRef}
            placement="bottom-start"
            variant="outlined"
            sx={{
              p: 1,
              minWidth: 280,
              maxHeight: 420,
              overflowY: 'auto',
              backgroundColor: 'background.popup',
              color: 'text.primary',
              borderColor: 'neutral.outlinedBorder',
              boxShadow: 'lg',
              backdropFilter: 'saturate(1.1)',
            }}
          >
            <Box
              component="label"
              onClick={(e) => e.stopPropagation()}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                px: 1,
                py: 0.75,
                borderRadius: 'sm',
                cursor: 'pointer',
                '&:hover': {
                  backgroundColor: 'var(--joy-palette-neutral-softHoverBg)',
                },
              }}
            >
              <Checkbox
                size="sm"
                checked={allOn}
                indeterminate={!allOn && selected.length > 0}
                onChange={toggleAll}
              />
              <Typography level="body-sm" sx={{ fontWeight: 700 }}>
                All calendars
              </Typography>
            </Box>

            {groups.map((g, gi) => {
              const state = groupState(g);
              return (
                <React.Fragment key={g.kind}>
                  <Divider sx={{ my: 0.5 }} />
                  <Box
                    component="label"
                    onClick={(e) => e.stopPropagation()}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                      px: 1,
                      py: 0.5,
                      borderRadius: 'sm',
                      cursor: 'pointer',
                      '&:hover': {
                  backgroundColor: 'var(--joy-palette-neutral-softHoverBg)',
                },
                    }}
                  >
                    <Checkbox
                      size="sm"
                      checked={state === 'all'}
                      indeterminate={state === 'some'}
                      onChange={() => toggleGroup(g)}
                    />
                    <Typography
                      level="body-xs"
                      textColor="text.tertiary"
                      sx={{
                        textTransform: 'uppercase',
                        letterSpacing: '0.14em',
                        fontWeight: 700,
                        flex: 1,
                      }}
                    >
                      {g.label}
                    </Typography>
                    <Typography level="body-xs" textColor="text.tertiary">
                      {g.options.filter((o) => selectedSet.has(o.id)).length}
                      /{g.options.length}
                    </Typography>
                  </Box>
                  {g.options.map((o) => (
                    <Box
                      key={o.id}
                      component="label"
                      onClick={(e) => e.stopPropagation()}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        pl: 3.5,
                        pr: 1,
                        py: 0.5,
                        borderRadius: 'sm',
                        cursor: 'pointer',
                        '&:hover': {
                  backgroundColor: 'var(--joy-palette-neutral-softHoverBg)',
                },
                      }}
                    >
                      <Checkbox
                        size="sm"
                        checked={selectedSet.has(o.id)}
                        onChange={() => toggleOne(o.id)}
                      />
                      <Swatch color={o.color} />
                      <Typography level="body-sm" sx={{ flex: 1 }}>
                        {o.label}
                      </Typography>
                    </Box>
                  ))}
                  {gi === groups.length - 1 ? null : null}
                </React.Fragment>
              );
            })}
          </Menu>
        </Dropdown>
      </Stack>
    </Stack>
  );
}

export default CalendarFilterBar;
