'use client';
/**
 * @file components/subgroups/CreateSubgroupModal.tsx
 * @brief Modal to create a new subgroup with auto-slug, cover upload, and initial owner.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import {
  Button,
  Modal,
  Input,
  Textarea,
  Select,
  Option,
  IconButton,
} from '@/components/ui';
import { MediaThumb } from '@/components/galleries/MediaThumb';
import { Avatar } from '@/components/ui';
import { useCreateSubgroup } from '@/hooks/useSubgroups';
import { useMediaUpload } from '@/hooks/useMediaUpload';
import { slugify, isValidSlugFormat } from '@/lib/slug';
import { getSubgroup } from '@/lib/api/subgroups';
import { searchAll } from '@/lib/api/search';
import type { SearchResultItem } from '@/lib/api/search';

interface User {
  id: string;
  display_name?: string;
  username?: string;
  avatar_url?: string | null;
}

export function CreateSubgroupModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const create = useCreateSubgroup();
  const mediaUpload = useMediaUpload();

  const [name, setName] = React.useState('');
  const [slug, setSlug] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [joinPolicy, setJoinPolicy] = React.useState<
    'open' | 'invite_only' | 'admin_approval'
  >('open');
  const [slugTouched, setSlugTouched] = React.useState(false);
  const [slugStatus, setSlugStatus] = React.useState<
    'valid' | 'invalid_format' | 'taken' | 'checking'
  >('valid');
  const [coverMediaId, setCoverMediaId] = React.useState<string | null>(null);
  const [assignOwner, setAssignOwner] = React.useState(false);
  const [selectedOwner, setSelectedOwner] = React.useState<User | null>(null);
  const [ownerSearchQuery, setOwnerSearchQuery] = React.useState('');
  const [ownerSuggestions, setOwnerSuggestions] = React.useState<SearchResultItem[]>([]);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const slugCheckTimeoutRef = React.useRef<NodeJS.Timeout | undefined>(undefined);

  // Auto-slug on name change unless user has manually edited
  React.useEffect(() => {
    if (!slugTouched && name) {
      setSlug(slugify(name));
      setSlugStatus('valid');
    }
  }, [name, slugTouched]);

  // Slug format validation
  React.useEffect(() => {
    if (!slug) {
      setSlugStatus('valid');
      return;
    }
    if (!isValidSlugFormat(slug)) {
      setSlugStatus('invalid_format');
      return;
    }
    // Trigger uniqueness check with debounce
    setSlugStatus('checking');
    if (slugCheckTimeoutRef.current) {
      clearTimeout(slugCheckTimeoutRef.current);
    }
    slugCheckTimeoutRef.current = setTimeout(async () => {
      try {
        await getSubgroup(slug);
        setSlugStatus('taken');
      } catch (err) {
        // 404 or other error means slug is available
        setSlugStatus('valid');
      }
    }, 400);
  }, [slug]);

  // Owner search with debounce
  React.useEffect(() => {
    if (!ownerSearchQuery.trim()) {
      setOwnerSuggestions([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const resp = await searchAll(ownerSearchQuery, { types: ['users'] });
        setOwnerSuggestions(resp.items);
      } catch (_err) {
        setOwnerSuggestions([]);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [ownerSearchQuery]);

  const handleCoverUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const mediaId = await mediaUpload.mutateAsync(file);
      setCoverMediaId(mediaId);
    } catch (_err) {
      // Error handled by useMediaUpload
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (slugStatus !== 'valid') return;

    await create.mutateAsync({
      name,
      slug,
      description: description || null,
      join_policy: joinPolicy,
      cover_media_id: coverMediaId,
      initial_owner_id: selectedOwner?.id,
    });

    setName('');
    setSlug('');
    setDescription('');
    setSlugTouched(false);
    setCoverMediaId(null);
    setAssignOwner(false);
    setSelectedOwner(null);
    setOwnerSearchQuery('');
    onClose();
  };

  const canSubmit = slugStatus === 'valid' && name.trim() && slug.trim();

  return (
    <Modal open={open} onClose={onClose} title="New group">
      <Stack component="form" spacing={2} onSubmit={submit}>
        <FormControl required>
          <FormLabel>Name</FormLabel>
          <Input value={name} onChange={(e) => setName(e.target.value)} required />
        </FormControl>

        <FormControl required>
          <FormLabel>Slug</FormLabel>
          <Input
            value={slug}
            onChange={(e) => {
              setSlug(e.target.value);
              setSlugTouched(true);
            }}
            error={slugStatus === 'invalid_format' || slugStatus === 'taken'}
            slotProps={{
              input: { pattern: '^[a-z0-9][a-z0-9_-]*$' },
            }}
            required
          />
          <Typography
            level="body-xs"
            sx={{
              mt: 0.5,
              color:
                slugStatus === 'invalid_format'
                  ? 'danger'
                  : slugStatus === 'taken'
                    ? 'danger'
                    : slugStatus === 'checking'
                      ? 'warning'
                      : 'success',
            }}
          >
            {slugStatus === 'invalid_format'
              ? 'Must start with a letter or number, contain only letters, numbers, dashes, or underscores.'
              : slugStatus === 'taken'
                ? 'This slug is taken.'
                : slugStatus === 'checking'
                  ? 'Checking availability…'
                  : 'Available'}
          </Typography>
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
              setJoinPolicy(
                (v as 'open' | 'invite_only' | 'admin_approval') ?? 'open',
              )
            }
          >
            <Option value="open">Open</Option>
            <Option value="invite_only">Invite only</Option>
            <Option value="admin_approval">Admin approval</Option>
          </Select>
        </FormControl>

        {/* Cover image upload */}
        <FormControl>
          <FormLabel>Cover image (optional)</FormLabel>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
            }}
          >
            {coverMediaId ? (
              <Box
                sx={{
                  position: 'relative',
                  width: 100,
                  height: 80,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: '4px',
                  overflow: 'hidden',
                }}
              >
                <MediaThumb mediaId={coverMediaId} alt="Cover preview" />
                <Button
                  size="sm"
                  variant="solid"
                  color="danger"
                  onClick={() => setCoverMediaId(null)}
                  sx={{
                    position: 'absolute',
                    bottom: 4,
                    right: 4,
                  }}
                >
                  Remove
                </Button>
              </Box>
            ) : (
              <>
                <Button
                  type="button"
                  variant="soft"
                  onClick={() => fileInputRef.current?.click()}
                  loading={mediaUpload.isPending}
                >
                  Upload cover
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  hidden
                  onChange={handleCoverUpload}
                />
              </>
            )}
          </Box>
        </FormControl>

        {/* Assign owner toggle */}
        <FormControl>
          <Button
            type="button"
            variant="plain"
            color="neutral"
            size="sm"
            onClick={() => {
              setAssignOwner(!assignOwner);
              if (assignOwner) {
                setSelectedOwner(null);
                setOwnerSearchQuery('');
              }
            }}
            sx={{ justifyContent: 'flex-start', pl: 0 }}
          >
            {assignOwner ? '✓ ' : ''}Assign to someone else (optional)
          </Button>
        </FormControl>

        {assignOwner && (
          <FormControl>
            <FormLabel>Owner</FormLabel>
            <Input
              placeholder="Search for a user…"
              value={ownerSearchQuery}
              onChange={(e) => setOwnerSearchQuery(e.target.value)}
            />
            {ownerSuggestions.length > 0 && (
              <Box
                sx={{
                  mt: 1,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: '4px',
                  maxHeight: 200,
                  overflowY: 'auto',
                }}
              >
                {ownerSuggestions.map((item) => (
                  <Box
                    key={item.id}
                    onClick={() => {
                      setSelectedOwner({
                        id: item.id,
                        display_name: item.title,
                      });
                      setOwnerSearchQuery('');
                    }}
                    sx={{
                      p: 1,
                      cursor: 'pointer',
                      '&:hover': { bgcolor: 'background.level1' },
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                    }}
                  >
                    <Avatar size="sm">{item.title.charAt(0).toUpperCase()}</Avatar>
                    <Typography level="body-sm">{item.title}</Typography>
                  </Box>
                ))}
              </Box>
            )}
            {selectedOwner && (
              <Box
                sx={{
                  mt: 1,
                  p: 1,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Avatar size="sm">
                    {selectedOwner.display_name?.charAt(0).toUpperCase() ?? 'U'}
                  </Avatar>
                  <Typography level="body-sm">{selectedOwner.display_name}</Typography>
                </Box>
                <Button
                  type="button"
                  variant="plain"
                  color="danger"
                  size="sm"
                  onClick={() => setSelectedOwner(null)}
                >
                  Clear
                </Button>
              </Box>
            )}
          </FormControl>
        )}

        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <Button
            variant="plain"
            color="neutral"
            onClick={onClose}
            type="button"
          >
            Cancel
          </Button>
          <Button type="submit" loading={create.isPending} disabled={!canSubmit}>
            Create
          </Button>
        </Stack>
      </Stack>
    </Modal>
  );
}
