'use client';
/**
 * @file components/subgroups/SubgroupDrawer.tsx
 * @brief Right drawer with Posts/Members/Settings tabs for a subgroup.
 *        URL-driven via ?subgroup=<slug> query param.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import {
  Drawer,
  Tabs,
  TabList,
  Tab,
  TabPanel,
  Input,
  Textarea,
  Select,
  Option,
  Button,
  EmptyState,
  Skeleton,
} from '@/components/ui';
import { useSubgroupDetail, useUpdateSubgroup } from '@/hooks/useSubgroups';
import { MembersList } from './MembersList';
import type { SubgroupDetail, UpdateSubgroupBody } from '@/lib/api/subgroups';

export interface SubgroupDrawerProps {
  slug: string | null;
  onClose: () => void;
}

export function SubgroupDrawer({ slug, onClose }: SubgroupDrawerProps) {
  const open = !!slug;
  const { data, isLoading } = useSubgroupDetail(slug);
  const canManage = data?.my_role === 'owner' || data?.my_role === 'moderator';

  return (
    <Drawer open={open} onClose={onClose} title={data?.name ?? 'Subgroup'}>
      {isLoading && <Skeleton height={120} />}
      {!isLoading && data && (
        <Tabs defaultValue="posts">
          <TabList>
            <Tab value="posts">Posts</Tab>
            <Tab value="members">Members ({data.member_count})</Tab>
            {canManage && <Tab value="settings">Settings</Tab>}
          </TabList>
          <TabPanel value="posts">
            <EmptyState title="Posts coming soon" description="Subgroup post feed lives here." />
          </TabPanel>
          <TabPanel value="members">
            <MembersList slug={data.slug} canManage={canManage} />
          </TabPanel>
          {canManage && (
            <TabPanel value="settings">
              <SettingsForm key={data.slug} subgroup={data} />
            </TabPanel>
          )}
        </Tabs>
      )}
    </Drawer>
  );
}

function SettingsForm({ subgroup }: { subgroup: SubgroupDetail }) {
  const update = useUpdateSubgroup(subgroup.slug);
  const [name, setName] = React.useState(subgroup.name);
  const [description, setDescription] = React.useState(subgroup.description ?? '');
  const [joinPolicy, setJoinPolicy] = React.useState<UpdateSubgroupBody['join_policy']>(
    subgroup.join_policy,
  );
  const [isPrivate, setIsPrivate] = React.useState(subgroup.is_private);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    update.mutate({ name, description, join_policy: joinPolicy, is_private: isPrivate });
  };

  return (
    <Stack component="form" spacing={2} onSubmit={submit}>
      <FormControl>
        <FormLabel>Name</FormLabel>
        <Input value={name} onChange={(e) => setName(e.target.value)} required />
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
            setJoinPolicy((v as UpdateSubgroupBody['join_policy']) ?? 'open')
          }
        >
          <Option value="open">Open</Option>
          <Option value="invite_only">Invite only</Option>
          <Option value="admin_approval">Admin approval</Option>
        </Select>
      </FormControl>
      <FormControl>
        <Stack direction="row" spacing={1} alignItems="center">
          <input
            id="is-private"
            type="checkbox"
            checked={isPrivate}
            onChange={(e) => setIsPrivate(e.target.checked)}
          />
          <Typography component="label" htmlFor="is-private" level="body-sm">
            Hide from discovery (private)
          </Typography>
        </Stack>
      </FormControl>
      <Button type="submit" loading={update.isPending}>
        Save changes
      </Button>
    </Stack>
  );
}

export default SubgroupDrawer;
