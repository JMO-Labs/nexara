/**
 * @file app/app/subgroups/[slug]/page.tsx
 * @brief Group hub detail page shell.
 */
'use client';

import { use } from 'react';
import { GroupHub } from '@/components/subgroups/hub/GroupHub';

export default function SubgroupHubPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  return <GroupHub slug={slug} />;
}
