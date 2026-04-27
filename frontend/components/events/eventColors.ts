/**
 * @file components/events/eventColors.ts
 * @brief Deterministic color assignment for events. Community events take the
 *        brand accent; subgroup events hash to a fixed editorial palette so the
 *        same group always renders the same hue across calendar bars, rail
 *        dots, and the detail panel.
 */
import type { EventItem } from '@/lib/api/events';

export interface EventTone {
  /** Solid bar / dot / accent color. */
  solid: string;
  /** Translucent fill for soft surfaces. */
  soft: string;
  /** Foreground for text on `solid`. */
  onSolid: string;
  /** Foreground for text on `soft`. */
  onSoft: string;
  /** Short label, e.g. "Community" or subgroup name (caller may override). */
  label: string;
}

const PALETTE: Omit<EventTone, 'label'>[] = [
  { solid: '#1f6feb', soft: 'rgba(31,111,235,0.14)', onSolid: '#fff', onSoft: '#1f6feb' }, // azure
  { solid: '#c2410c', soft: 'rgba(194,65,12,0.14)', onSolid: '#fff', onSoft: '#9a3412' },  // burnt orange
  { solid: '#15803d', soft: 'rgba(21,128,61,0.14)', onSolid: '#fff', onSoft: '#166534' },  // pine
  { solid: '#7c3aed', soft: 'rgba(124,58,237,0.14)', onSolid: '#fff', onSoft: '#6d28d9' }, // violet
  { solid: '#be185d', soft: 'rgba(190,24,93,0.14)', onSolid: '#fff', onSoft: '#9d174d' },  // magenta
  { solid: '#0d9488', soft: 'rgba(13,148,136,0.14)', onSolid: '#fff', onSoft: '#0f766e' }, // teal
  { solid: '#a16207', soft: 'rgba(161,98,7,0.14)', onSolid: '#fff', onSoft: '#854d0e' },   // amber
];

const COMMUNITY: Omit<EventTone, 'label'> = {
  solid: 'var(--joy-palette-primary-solidBg, #0b7285)',
  soft: 'rgba(11,114,133,0.12)',
  onSolid: '#fff',
  onSoft: 'var(--joy-palette-primary-plainColor, #0b7285)',
};

function hashStr(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function toneForEvent(
  ev: Pick<EventItem, 'visibility' | 'subgroup_id'>,
  subgroupNames?: Map<string, string>,
): EventTone {
  if (ev.visibility !== 'subgroup' || !ev.subgroup_id) {
    return { ...COMMUNITY, label: 'Community' };
  }
  const idx = hashStr(ev.subgroup_id) % PALETTE.length;
  return {
    ...PALETTE[idx],
    label: subgroupNames?.get(ev.subgroup_id) ?? 'Subgroup',
  };
}

export function toneForSubgroupId(id: string | null): EventTone {
  if (!id) return { ...COMMUNITY, label: 'Community' };
  const idx = hashStr(id) % PALETTE.length;
  return { ...PALETTE[idx], label: 'Subgroup' };
}
