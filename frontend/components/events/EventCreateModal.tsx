'use client';
/**
 * @file components/events/EventCreateModal.tsx
 * @brief Form modal for creating or editing an event. Pass `event` to switch
 *        into edit mode (prefills fields, calls updateEvent on submit).
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import Box from '@mui/joy/Box';
import Autocomplete from '@mui/joy/Autocomplete';
import { Modal, Input, Textarea, Button, Select, Option } from '@/components/ui';
import Typography from '@mui/joy/Typography';
import { useCreateEvent, useUpdateEvent } from '@/hooks/useEvents';
import { useCalendars } from '@/hooks/useCalendars';
import { useUserLocation } from '@/hooks/useUserLocation';
import { geocodeSearch, type GeocodeResult } from '@/lib/api/geocode';
import type { EventItem } from '@/lib/api/events';
import { EVENT_COLOR_PRESETS } from './eventColors';

interface LocationFieldProps {
  value: string;
  onChange: (next: string, coords: { lat: number; lon: number } | null) => void;
}

function LocationField({ value, onChange }: LocationFieldProps) {
  const userLoc = useUserLocation();
  const [input, setInput] = React.useState(value);
  const [options, setOptions] = React.useState<GeocodeResult[]>([]);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    setInput(value);
  }, [value]);

  // Debounced search.
  React.useEffect(() => {
    const q = input.trim();
    if (q.length < 2) {
      setOptions([]);
      return;
    }
    if (q === value.trim()) {
      return;
    }
    const ctrl = new AbortController();
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const results = await geocodeSearch(q, {
          bias: userLoc ? { lat: userLoc.lat, lon: userLoc.lon } : undefined,
          signal: ctrl.signal,
        });
        setOptions(results);
      } catch {
        setOptions([]);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [input, value, userLoc]);

  return (
    <Autocomplete
      freeSolo
      autoComplete
      filterOptions={(x) => x}
      options={options}
      loading={loading}
      getOptionLabel={(opt) => (typeof opt === 'string' ? opt : opt.label)}
      isOptionEqualToValue={(a, b) =>
        typeof a !== 'string' && typeof b !== 'string' && a.osm_id === b.osm_id
      }
      renderOption={(props, opt) => {
        const o = opt as GeocodeResult;
        const key = o.osm_id ?? `${o.label}@${o.lat},${o.lon}`;
        return (
          <li {...props} key={key}>
            {o.label}
          </li>
        );
      }}
      value={value}
      inputValue={input}
      onInputChange={(_e, v) => setInput(v)}
      onChange={(_e, v) => {
        if (v == null) {
          onChange('', null);
        } else if (typeof v === 'string') {
          onChange(v, null);
        } else {
          onChange(v.label, { lat: v.lat, lon: v.lon });
        }
      }}
      onBlur={() => {
        // Free-text edit (no suggestion picked) → coords cleared.
        if (input !== value) onChange(input, null);
      }}
      placeholder="Address, place, or venue"
      slotProps={{
        listbox: {
          sx: {
            maxHeight: 280,
            backgroundColor: 'background.popup',
            color: 'text.primary',
            borderColor: 'neutral.outlinedBorder',
            boxShadow: 'lg',
            '& li': {
              color: 'text.primary',
              cursor: 'pointer',
              padding: '6px 12px',
              '&:hover, &.Mui-focused': {
                backgroundColor: 'var(--joy-palette-neutral-softHoverBg)',
              },
              '&[aria-selected="true"]': {
                backgroundColor: 'var(--joy-palette-neutral-softActiveBg)',
              },
            },
          },
        },
      }}
    />
  );
}

interface TimeFieldProps {
  value: string;
  onChange: (next: string) => void;
}

function TimeField({ value, onChange }: TimeFieldProps) {
  const [input, setInput] = React.useState(timeLabel(value));
  React.useEffect(() => {
    setInput(timeLabel(value));
  }, [value]);

  const commit = (raw: string) => {
    const parsed = parseTime(raw);
    if (parsed) {
      onChange(parsed);
      setInput(timeLabel(parsed));
    } else {
      setInput(timeLabel(value));
    }
  };

  return (
    <Autocomplete
      freeSolo
      options={TIME_OPTIONS.map((t) => t.value)}
      getOptionLabel={(opt) => {
        const v = typeof opt === 'string' ? opt : '';
        return parseTime(v) ? timeLabel(parseTime(v)!) : v;
      }}
      value={value}
      inputValue={input}
      onInputChange={(_e, v) => setInput(v)}
      onChange={(_e, v) => {
        if (typeof v === 'string') commit(v);
      }}
      onBlur={() => commit(input)}
      slotProps={{
        listbox: {
          sx: {
            maxHeight: 240,
            backgroundColor: 'background.popup',
            color: 'text.primary',
            borderColor: 'neutral.outlinedBorder',
            boxShadow: 'lg',
            '& [role="option"]': {
              color: 'text.primary',
              '&:hover': {
                backgroundColor: 'var(--joy-palette-neutral-softHoverBg)',
              },
              '&[aria-selected="true"]': {
                backgroundColor: 'var(--joy-palette-neutral-softActiveBg)',
              },
            },
          },
        },
      }}
    />
  );
}

export interface EventCreateModalProps {
  open: boolean;
  onClose: () => void;
  /** When provided, modal switches to edit mode. */
  event?: EventItem | null;
}

const PAD = (n: number) => String(n).padStart(2, '0');

function splitLocal(iso: string): { date: string; time: string } {
  const d = new Date(iso);
  return {
    date: `${d.getFullYear()}-${PAD(d.getMonth() + 1)}-${PAD(d.getDate())}`,
    time: `${PAD(d.getHours())}:${PAD(d.getMinutes())}`,
  };
}

function todayDate(): string {
  const d = new Date();
  return `${d.getFullYear()}-${PAD(d.getMonth() + 1)}-${PAD(d.getDate())}`;
}

/** 30-min increments across 24h: ["00:00","00:30",...,"23:30"]. */
const TIME_OPTIONS: { value: string; label: string }[] = Array.from(
  { length: 48 },
  (_, i) => {
    const h = Math.floor(i / 2);
    const m = i % 2 === 0 ? 0 : 30;
    const value = `${PAD(h)}:${PAD(m)}`;
    const h12 = h % 12 === 0 ? 12 : h % 12;
    const ampm = h < 12 ? 'AM' : 'PM';
    return { value, label: `${h12}:${PAD(m)} ${ampm}` };
  },
);

const DEFAULT_START_TIME = '09:00';
const DEFAULT_END_TIME = '10:00';

/** Dark-mode-aware listbox styling for Select dropdowns in this modal. */
const SELECT_SLOT_PROPS = {
  listbox: {
    sx: {
      backgroundColor: 'background.popup',
      color: 'text.primary',
      borderColor: 'neutral.outlinedBorder',
      boxShadow: 'lg',
      '--ListItem-radius': '6px',
      '& [role="option"]': {
        color: 'text.primary',
        '&:hover': {
          backgroundColor: 'var(--joy-palette-neutral-softHoverBg)',
        },
        '&[aria-selected="true"]': {
          backgroundColor: 'var(--joy-palette-neutral-softActiveBg)',
          color: 'text.primary',
        },
      },
    },
  },
} as const;

/** Compose local-date + HH:mm into ISO string. */
function composeIso(date: string, time: string): string {
  const [h, m] = time.split(':').map(Number);
  const [y, mo, d] = date.split('-').map(Number);
  return new Date(y, mo - 1, d, h, m, 0, 0).toISOString();
}

/** Parse free-form time input → canonical "HH:mm" (24h). Returns null if invalid.
 * Accepts: "9", "9am", "9:12", "09:12", "9:12 am", "9:12pm", "21:30". */
function parseTime(raw: string): string | null {
  const s = raw.trim().toLowerCase().replace(/\s+/g, '');
  if (!s) return null;
  const m = s.match(/^(\d{1,2})(?::(\d{1,2}))?(am|pm)?$/);
  if (!m) return null;
  let h = parseInt(m[1], 10);
  const min = m[2] ? parseInt(m[2], 10) : 0;
  const ampm = m[3];
  if (Number.isNaN(h) || Number.isNaN(min) || min > 59) return null;
  if (ampm) {
    if (h < 1 || h > 12) return null;
    if (ampm === 'am') h = h === 12 ? 0 : h;
    else h = h === 12 ? 12 : h + 12;
  } else if (h > 23) return null;
  return `${PAD(h)}:${PAD(min)}`;
}

function timeLabel(value: string): string {
  const [h, m] = value.split(':').map(Number);
  const h12 = h % 12 === 0 ? 12 : h % 12;
  const ampm = h < 12 ? 'AM' : 'PM';
  return `${h12}:${PAD(m)} ${ampm}`;
}

export function EventCreateModal({ open, onClose, event }: EventCreateModalProps) {
  const create = useCreateEvent();
  const update = useUpdateEvent(event?.id ?? '');
  const isEdit = !!event;

  const [title, setTitle] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [location, setLocation] = React.useState('');
  const [coords, setCoords] = React.useState<{ lat: number; lon: number } | null>(null);
  const [startDate, setStartDate] = React.useState('');
  const [startTime, setStartTime] = React.useState(DEFAULT_START_TIME);
  const [endDate, setEndDate] = React.useState('');
  const [endTime, setEndTime] = React.useState(DEFAULT_END_TIME);
  const [allDay, setAllDay] = React.useState(false);
  const [visibility, setVisibility] = React.useState<'community' | 'subgroup' | 'private'>(
    'community',
  );
  const [subgroupId, setSubgroupId] = React.useState<string | null>(null);
  const [color, setColor] = React.useState<string | null>(null);

  const { data: calendars } = useCalendars();
  const myGroups = React.useMemo(
    () =>
      (calendars ?? [])
        .filter((c) => c.kind === 'subgroup' && c.subgroup_id)
        .map((c) => ({ id: c.subgroup_id as string, name: c.name })),
    [calendars],
  );

  React.useEffect(() => {
    if (!open) return;
    if (event) {
      setTitle(event.title);
      setDescription(event.description ?? '');
      setLocation(event.location ?? '');
      setCoords(
        event.latitude != null && event.longitude != null
          ? { lat: event.latitude, lon: event.longitude }
          : null,
      );
      const s = splitLocal(event.starts_at);
      const e = splitLocal(event.ends_at);
      setStartDate(s.date);
      setStartTime(event.is_all_day ? DEFAULT_START_TIME : s.time);
      setEndDate(e.date);
      setEndTime(event.is_all_day ? DEFAULT_END_TIME : e.time);
      setAllDay(event.is_all_day);
      setVisibility(event.visibility as 'community' | 'subgroup' | 'private');
      setSubgroupId(event.subgroup_id ?? null);
      setColor(event.color);
    } else {
      const today = todayDate();
      setTitle('');
      setDescription('');
      setLocation('');
      setCoords(null);
      setStartDate(today);
      setStartTime(DEFAULT_START_TIME);
      setEndDate(today);
      setEndTime(DEFAULT_END_TIME);
      setAllDay(false);
      setVisibility('community');
      setSubgroupId(null);
      setColor(null);
    }
  }, [open, event]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const startsIso = allDay
      ? composeIso(startDate, '00:00')
      : composeIso(startDate, startTime);
    const endsIso = allDay
      ? composeIso(endDate, '23:59')
      : composeIso(endDate, endTime);
    if (visibility === 'subgroup' && !subgroupId) {
      return;
    }
    const body = {
      title,
      description: description || null,
      location: location || null,
      starts_at: startsIso,
      ends_at: endsIso,
      is_all_day: allDay,
      visibility,
      subgroup_id: visibility === 'subgroup' ? subgroupId : null,
      color,
      latitude: coords?.lat ?? null,
      longitude: coords?.lon ?? null,
    };
    if (isEdit) await update.mutateAsync(body);
    else await create.mutateAsync(body);
    onClose();
  };

  const pending = isEdit ? update.isPending : create.isPending;

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? 'Edit event' : 'New event'}>
      <Stack component="form" spacing={2} onSubmit={submit}>
        <FormControl required>
          <FormLabel>Title</FormLabel>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </FormControl>
        <FormControl>
          <FormLabel>Description</FormLabel>
          <Textarea
            minRows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </FormControl>
        <FormControl>
          <FormLabel>Location</FormLabel>
          <LocationField
            value={location}
            onChange={(label, c) => {
              setLocation(label);
              setCoords(c);
            }}
          />
          <Typography level="body-xs" textColor="text.tertiary" sx={{ mt: 0.5 }}>
            Suggestions via Photon · © OpenStreetMap contributors
          </Typography>
        </FormControl>
        <FormControl>
          <Stack direction="row" spacing={1} alignItems="center">
            <input
              id="allday"
              type="checkbox"
              checked={allDay}
              onChange={(e) => setAllDay(e.target.checked)}
            />
            <FormLabel htmlFor="allday" sx={{ m: 0 }}>
              All day
            </FormLabel>
          </Stack>
        </FormControl>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <FormControl required sx={{ flex: 1 }}>
            <FormLabel>Start date</FormLabel>
            <Input
              type="date"
              value={startDate}
              onChange={(e) => {
                const v = e.target.value;
                setStartDate(v);
                if (!endDate || endDate < v) setEndDate(v);
              }}
              required
            />
          </FormControl>
          {!allDay && (
            <FormControl required sx={{ flex: 1 }}>
              <FormLabel>Start time</FormLabel>
              <TimeField value={startTime} onChange={setStartTime} />
            </FormControl>
          )}
        </Stack>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <FormControl required sx={{ flex: 1 }}>
            <FormLabel>End date</FormLabel>
            <Input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
            />
          </FormControl>
          {!allDay && (
            <FormControl required sx={{ flex: 1 }}>
              <FormLabel>End time</FormLabel>
              <TimeField value={endTime} onChange={setEndTime} />
            </FormControl>
          )}
        </Stack>
        <FormControl>
          <FormLabel>Visibility</FormLabel>
          <Select
            value={visibility}
            onChange={(_e, v) => {
              const next = (v as 'community' | 'subgroup' | 'private') ?? 'community';
              setVisibility(next);
              if (next !== 'subgroup') setSubgroupId(null);
            }}
            slotProps={SELECT_SLOT_PROPS}
          >
            <Option value="community">Community</Option>
            <Option value="subgroup">Group</Option>
            <Option value="private">Personal</Option>
          </Select>
        </FormControl>
        {visibility === 'subgroup' && (
          <FormControl required error={!subgroupId}>
            <FormLabel>Group</FormLabel>
            <Select
              value={subgroupId ?? ''}
              placeholder={
                myGroups.length === 0 ? 'No groups available' : 'Select a group'
              }
              disabled={myGroups.length === 0}
              onChange={(_e, v) => setSubgroupId((v as string) || null)}
              slotProps={SELECT_SLOT_PROPS}
            >
              {myGroups.map((g) => (
                <Option key={g.id} value={g.id}>
                  {g.name}
                </Option>
              ))}
            </Select>
          </FormControl>
        )}
        <FormControl>
          <FormLabel>Color</FormLabel>
          <Stack direction="row" spacing={0.75} sx={{ flexWrap: 'wrap', rowGap: 0.75 }}>
            <Box
              role="button"
              tabIndex={0}
              aria-label="Default (no override)"
              aria-pressed={color === null}
              onClick={() => setColor(null)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setColor(null);
                }
              }}
              sx={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                cursor: 'pointer',
                border: '2px solid',
                borderColor: color === null ? 'primary.solidBg' : 'divider',
                background:
                  'repeating-linear-gradient(45deg, var(--nx-palette-background-level1) 0 6px, var(--nx-palette-background-level2) 6px 12px)',
              }}
            />
            {EVENT_COLOR_PRESETS.map((p) => (
              <Box
                key={p.value}
                role="button"
                tabIndex={0}
                aria-label={p.name}
                aria-pressed={color === p.value}
                title={p.name}
                onClick={() => setColor(p.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setColor(p.value);
                  }
                }}
                sx={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  backgroundColor: p.value,
                  cursor: 'pointer',
                  border: '2px solid',
                  borderColor: color === p.value ? 'text.primary' : 'transparent',
                  boxShadow:
                    color === p.value
                      ? `0 0 0 2px ${p.value}`
                      : 'inset 0 0 0 1px rgba(0,0,0,0.1)',
                  transition: 'transform 120ms ease',
                  '&:hover': { transform: 'scale(1.08)' },
                }}
              />
            ))}
            <Box
              component="label"
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 0.5,
                ml: 1,
                cursor: 'pointer',
                fontSize: 12,
                color: 'text.tertiary',
              }}
            >
              <Box
                component="input"
                type="color"
                value={color ?? '#1f6feb'}
                onChange={(e) => setColor((e.target as HTMLInputElement).value)}
                sx={{
                  width: 28,
                  height: 28,
                  border: 'none',
                  background: 'transparent',
                  p: 0,
                  cursor: 'pointer',
                }}
              />
              Custom
            </Box>
          </Stack>
        </FormControl>
        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <Button variant="plain" color="neutral" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={pending}>
            {isEdit ? 'Save' : 'Create'}
          </Button>
        </Stack>
      </Stack>
    </Modal>
  );
}

export default EventCreateModal;
