/**
 * @file components/subgroups/hub/MemberOnlyGate.tsx
 * @brief Non-member view for restricted groups: cover + info + CTA.
 */
'use client';

import * as React from 'react';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Button from '@mui/joy/Button';
import { CoverBand } from './CoverBand';
import type { SubgroupDetail } from '@/lib/api/subgroups';

export interface MemberOnlyGateProps {
  subgroup: SubgroupDetail;
}

export function MemberOnlyGate({ subgroup }: MemberOnlyGateProps) {
  const ctaText =
    subgroup.join_policy === 'admin_approval' ? 'Request to join' : 'Invite required';

  return (
    <Stack spacing={4} sx={{ width: '100%', maxWidth: 600, mx: 'auto' }}>
      <CoverBand subgroup={subgroup} />
      <Stack spacing={2} sx={{ px: { xs: 2, md: 0 } }}>
        <Typography level="h2" component="h1">
          {subgroup.name}
        </Typography>
        {subgroup.description && (
          <Typography level="body-md" sx={{ color: 'text.secondary' }}>
            {subgroup.description}
          </Typography>
        )}
        <Button disabled size="lg" sx={{ mt: 2 }}>
          {ctaText}
        </Button>
      </Stack>
    </Stack>
  );
}

export default MemberOnlyGate;
