'use client';
/**
 * @file app/app/subgroups/page.tsx
 * @brief Subgroups list view; opens detail drawer via ?subgroup=<slug>.
 */
import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Button, Modal, Input, Textarea, Select, Option } from '@/components/ui';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import { SubgroupList } from '@/components/subgroups/SubgroupList';
import { SubgroupDrawer } from '@/components/subgroups/SubgroupDrawer';
import { useCreateSubgroup } from '@/hooks/useSubgroups';

export default function SubgroupsPage() {
  const router = useRouter();
  const params = useSearchParams();
  const slug = params.get('subgroup');
  const [createOpen, setCreateOpen] = React.useState(false);

  const select = (s: string) => {
    const next = new URLSearchParams(params.toString());
    next.set('subgroup', s);
    router.push(`/app/subgroups?${next}`);
  };
  const closeDrawer = () => {
    const next = new URLSearchParams(params.toString());
    next.delete('subgroup');
    router.push(next.toString() ? `/app/subgroups?${next}` : '/app/subgroups');
  };

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 1200, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 3 }}>
        <Typography level="h2" sx={{ fontFamily: 'var(--font-display)' }}>
          Subgroups
        </Typography>
        <Button onClick={() => setCreateOpen(true)}>New subgroup</Button>
      </Stack>
      <SubgroupList onSelect={select} />
      <SubgroupDrawer slug={slug} onClose={closeDrawer} />
      <CreateSubgroupModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </Box>
  );
}

function CreateSubgroupModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const create = useCreateSubgroup();
  const [name, setName] = React.useState('');
  const [slug, setSlug] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [joinPolicy, setJoinPolicy] = React.useState<'open' | 'invite_only' | 'admin_approval'>(
    'open',
  );

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create.mutateAsync({
      name,
      slug,
      description: description || null,
      join_policy: joinPolicy,
    });
    setName('');
    setSlug('');
    setDescription('');
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="New subgroup">
      <Stack component="form" spacing={2} onSubmit={submit}>
        <FormControl required>
          <FormLabel>Name</FormLabel>
          <Input value={name} onChange={(e) => setName(e.target.value)} required />
        </FormControl>
        <FormControl required>
          <FormLabel>Slug</FormLabel>
          <Input
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            slotProps={{ input: { pattern: '^[a-z0-9][a-z0-9_-]*$' } }}
            required
          />
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
          <FormLabel>Join policy</FormLabel>
          <Select
            value={joinPolicy}
            onChange={(_e, v) =>
              setJoinPolicy((v as 'open' | 'invite_only' | 'admin_approval') ?? 'open')
            }
          >
            <Option value="open">Open</Option>
            <Option value="invite_only">Invite only</Option>
            <Option value="admin_approval">Admin approval</Option>
          </Select>
        </FormControl>
        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <Button variant="plain" color="neutral" onClick={onClose} type="button">
            Cancel
          </Button>
          <Button type="submit" loading={create.isPending}>
            Create
          </Button>
        </Stack>
      </Stack>
    </Modal>
  );
}
