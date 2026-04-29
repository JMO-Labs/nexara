'use client';
/**
 * @file app/app/subgroups/page.tsx
 * @brief Editorial Groups index — oversized serif masthead, sticky glass
 *        toolbar, bento mosaic of group tiles. Drawer routing preserved
 *        via ?subgroup=<slug>.
 */
import * as React from 'react';
import { useRouter } from 'next/navigation';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { motion } from 'framer-motion';
import {
  Button,
  Input,
  Skeleton,
  EmptyState,
  Chip,
} from '@/components/ui';
import { SubgroupCard } from '@/components/subgroups/SubgroupCard';
import { CreateSubgroupModal } from '@/components/subgroups/CreateSubgroupModal';
import { PageMasthead } from '@/components/layout/PageMasthead';
import {
  useSubgroupList,
  useJoinSubgroup,
  useLeaveSubgroup,
} from '@/hooks/useSubgroups';
import type { Subgroup } from '@/lib/api/subgroups';

type FilterMode = 'all' | 'open' | 'private';

export default function SubgroupsPage() {
  const router = useRouter();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [query, setQuery] = React.useState('');
  const [filter, setFilter] = React.useState<FilterMode>('all');

  const { data, isLoading, error } = useSubgroupList();
  const join = useJoinSubgroup();
  const leave = useLeaveSubgroup();

  const select = (s: string) => {
    router.push(`/app/subgroups/${s}`);
  };

  const filtered = React.useMemo(() => {
    const list = data ?? [];
    const q = query.trim().toLowerCase();
    return list.filter((g) => {
      if (filter === 'open' && g.join_policy !== 'open') return false;
      if (filter === 'private' && !g.is_private) return false;
      // TODO: Add is_member flag to Subgroup type when available,
      // then filter: if (g.is_private && !is_member) return false;
      // For now, trust backend filtering for private group visibility.
      if (!q) return true;
      return (
        g.name.toLowerCase().includes(q) ||
        g.slug.toLowerCase().includes(q) ||
        (g.description ?? '').toLowerCase().includes(q)
      );
    });
  }, [data, query, filter]);

  const total = data?.length ?? 0;

  return (
    <Box
      sx={{
        position: 'relative',
        minHeight: '100vh',
        px: { xs: 2, md: 6, lg: 8 },
        pb: 10,
        width: '100%',
      }}
    >
      <PageMasthead
        title="Groups"
        meta={`${total} ${total === 1 ? 'circle' : 'circles'} in the community`}
        right={
          <Button onClick={() => setCreateOpen(true)}>+ New group</Button>
        }
      />

      {/* Sticky glass toolbar */}
      <Box
        sx={{
          position: 'sticky',
          top: 0,
          zIndex: 5,
          mx: { xs: -2, md: -6, lg: -8 },
          px: { xs: 2, md: 6, lg: 8 },
          py: 1.5,
          backdropFilter: 'saturate(140%) blur(12px)',
          WebkitBackdropFilter: 'saturate(140%) blur(12px)',
          background:
            'color-mix(in srgb, var(--joy-palette-background-body) 78%, transparent)',
          borderTop: '1px solid var(--joy-palette-divider)',
          borderBottom: '1px solid var(--joy-palette-divider)',
          mb: { xs: 4, md: 6 },
        }}
      >
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={{ xs: 1.5, sm: 3 }}
          alignItems={{ sm: 'center' }}
          justifyContent="space-between"
        >
          <Box sx={{ flex: 1, minWidth: 0, maxWidth: { sm: 420 } }}>
            <Input
              placeholder="Search groups…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              sx={{ width: '100%' }}
            />
          </Box>
          <Stack direction="row" spacing={0.75}>
            {(['all', 'open', 'private'] as FilterMode[]).map((m) => {
              const active = filter === m;
              return (
                <Chip
                  key={m}
                  size="sm"
                  variant={active ? 'solid' : 'soft'}
                  color={active ? 'primary' : 'neutral'}
                  onClick={() => setFilter(m)}
                  sx={{
                    cursor: 'pointer',
                    fontFamily: 'var(--font-mono, var(--font-body))',
                    fontSize: '11px',
                    letterSpacing: '0.18em',
                    textTransform: 'uppercase',
                  }}
                >
                  {m}
                </Chip>
              );
            })}
          </Stack>
        </Stack>
      </Box>

      <SectionLabel
        index="01"
        label={query ? 'Results' : filter === 'all' ? 'All groups' : `${filter} groups`}
        italic={
          query
            ? `for "${query}"`
            : `${filtered.length} ${filtered.length === 1 ? 'circle' : 'circles'}`
        }
      />

      <Box sx={{ mt: 3 }}>
        <GroupMosaic
          data={filtered}
          isLoading={isLoading}
          error={error}
          onSelect={select}
          onJoin={(s) => join.mutate(s)}
          onLeave={(s) => leave.mutate(s)}
          joinBusy={join.isPending ? join.variables : null}
          leaveBusy={leave.isPending ? leave.variables : null}
          onCreate={() => setCreateOpen(true)}
        />
      </Box>

      <CreateSubgroupModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </Box>
  );
}

/* ─────────────────────────────────────────────────────────────────
 * Section label — small caps numeral + italic kicker
 * ───────────────────────────────────────────────────────────────── */
function SectionLabel({
  index,
  label,
  italic,
}: {
  index: string;
  label: string;
  italic?: string;
}) {
  return (
    <Stack
      direction="row"
      alignItems="baseline"
      spacing={2}
      sx={{ borderBottom: '1px solid', borderColor: 'divider', pb: 1.5 }}
    >
      <Typography
        sx={{
          fontFamily: 'var(--font-display)',
          fontVariantNumeric: 'tabular-nums',
          fontSize: '11px',
          letterSpacing: '0.2em',
          color: 'text.tertiary',
        }}
      >
        {index}
      </Typography>
      <Typography
        sx={{
          fontFamily: 'var(--font-display)',
          fontSize: { xs: '22px', md: '28px' },
          fontWeight: 400,
          letterSpacing: '-0.01em',
          textTransform: 'capitalize',
        }}
      >
        {label}
      </Typography>
      {italic && (
        <Typography
          sx={{
            fontFamily: 'var(--font-display)',
            fontStyle: 'italic',
            fontSize: { xs: '14px', md: '16px' },
            color: 'text.tertiary',
            ml: 'auto !important',
          }}
        >
          {italic}
        </Typography>
      )}
    </Stack>
  );
}

/* ─────────────────────────────────────────────────────────────────
 * Bento mosaic — every 5th tile (anchored) spans 2 cols
 * ───────────────────────────────────────────────────────────────── */
function GroupMosaic({
  data,
  isLoading,
  error,
  onSelect,
  onJoin,
  onLeave,
  joinBusy,
  leaveBusy,
  onCreate,
}: {
  data: Subgroup[];
  isLoading: boolean;
  error: unknown;
  onSelect: (s: string) => void;
  onJoin: (s: string) => void;
  onLeave: (s: string) => void;
  joinBusy: string | null | undefined;
  leaveBusy: string | null | undefined;
  onCreate: () => void;
}) {
  if (error) {
    return (
      <EmptyState
        title="Couldn't load groups"
        description={String(error)}
        action={
          <Button variant="soft" onClick={() => window.location.reload()}>
            Retry
          </Button>
        }
      />
    );
  }
  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'grid',
          gap: { xs: 1.5, md: 2.5 },
          gridTemplateColumns: {
            xs: 'repeat(1, 1fr)',
            sm: 'repeat(2, 1fr)',
            lg: 'repeat(3, 1fr)',
          },
        }}
      >
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} height={i % 5 === 0 ? 360 : 240} />
        ))}
      </Box>
    );
  }
  if (data.length === 0) {
    return (
      <EmptyState
        title="No groups match"
        description="Try a different filter or start a new circle."
        action={
          <Button variant="solid" onClick={onCreate}>
            New group
          </Button>
        }
      />
    );
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gap: { xs: 1.5, md: 2.5 },
        gridTemplateColumns: {
          xs: 'repeat(1, 1fr)',
          sm: 'repeat(2, 1fr)',
          lg: 'repeat(3, 1fr)',
        },
        gridAutoFlow: 'dense',
      }}
    >
      {data.map((g, idx) => {
        const anchor = idx % 5 === 0;
        return (
          <motion.div
            key={g.id}
            layout
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.42,
              ease: [0.22, 1, 0.36, 1],
              delay: Math.min(idx * 0.025, 0.32),
            }}
            style={{
              gridColumn: anchor ? 'span 2' : undefined,
              display: 'flex',
            }}
          >
            <Box sx={{ flex: 1 }}>
              <SubgroupCard
                subgroup={g}
                anchor={anchor}
                isMember={!!g.my_role}
                onSelect={onSelect}
                onJoin={onJoin}
                onLeave={onLeave}
                busy={joinBusy === g.slug || leaveBusy === g.slug}
              />
            </Box>
          </motion.div>
        );
      })}
    </Box>
  );
}

