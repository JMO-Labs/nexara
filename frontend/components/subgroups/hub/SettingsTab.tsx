/**
 * @file components/subgroups/hub/SettingsTab.tsx
 * @brief Group settings tab with cover/logo upload.
 */
"use client";

import * as React from "react";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import FormControl from "@mui/joy/FormControl";
import FormLabel from "@mui/joy/FormLabel";
import FormHelperText from "@mui/joy/FormHelperText";
import { Input, Textarea, Select, Option, Button } from "@/components/ui";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { useUpdateSubgroup } from "@/hooks/useSubgroups";
import { useMediaUpload } from "@/hooks/useMediaUpload";
import { useToasts } from "@/stores/toasts";
import type { SubgroupDetail, UpdateSubgroupBody } from "@/lib/api/subgroups";

export interface SettingsTabProps {
  subgroup: SubgroupDetail;
}

export function SettingsTab({ subgroup }: SettingsTabProps) {
  const canManage =
    subgroup.my_role === "owner" || subgroup.my_role === "moderator";
  const update = useUpdateSubgroup(subgroup.slug);
  const mediaUpload = useMediaUpload();
  const toasts = useToasts();
  const [name, setName] = React.useState(subgroup.name);
  const [description, setDescription] = React.useState(
    subgroup.description ?? "",
  );
  const [joinPolicy, setJoinPolicy] = React.useState<
    UpdateSubgroupBody["join_policy"]
  >(subgroup.join_policy);
  const [isPrivate, setIsPrivate] = React.useState(subgroup.is_private);
  const [avatarUrl, setAvatarUrl] = React.useState(subgroup.avatar_url ?? "");
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const [coverMediaId, setCoverMediaId] = React.useState<string | null>(
    subgroup.cover_media_id ?? null,
  );

  if (!canManage) {
    return (
      <Stack spacing={2}>
        <Typography level="body-md" sx={{ color: "text.secondary" }}>
          You don&apos;t have permission to manage group settings.
        </Typography>
      </Stack>
    );
  }

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    update.mutate({
      name,
      description,
      join_policy: joinPolicy,
      is_private: isPrivate,
    });
  };

  const handleCoverUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files;
    if (!files || files.length === 0) return;

    const file = files[0];

    try {
      const mediaId = await mediaUpload.mutateAsync(file);
      setCoverMediaId(mediaId);
      update.mutate({ cover_media_id: mediaId });
    } catch (err) {
      toasts.push({
        variant: "danger",
        title: "Upload failed",
        message:
          err instanceof Error ? err.message : "Failed to upload cover image",
      });
    }
  };

  return (
    <Stack component="form" spacing={3} onSubmit={submit}>
      <FormControl>
        <FormLabel>Group name</FormLabel>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
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
            setJoinPolicy((v as UpdateSubgroupBody["join_policy"]) ?? "open")
          }
        >
          <Option value="open">Open (anyone can join)</Option>
          <Option value="invite_only">Invite only</Option>
          <Option value="admin_approval">Admin approval required</Option>
        </Select>
      </FormControl>

      <FormControl>
        <FormLabel>Private group</FormLabel>
        <Select
          value={isPrivate ? "true" : "false"}
          onChange={(_e, v) => setIsPrivate(v === "true")}
        >
          <Option value="false">Visible to all members</Option>
          <Option value="true">Visible only to members</Option>
        </Select>
        <FormHelperText>
          Private groups only appear to members in the directory.
        </FormHelperText>
      </FormControl>

      <FormControl>
        <FormLabel>Logo (avatar URL)</FormLabel>
        <Input
          value={avatarUrl}
          onChange={(e) => setAvatarUrl(e.target.value)}
          placeholder="https://example.com/logo.png"
        />
      </FormControl>

      <FormControl>
        <FormLabel>Cover image</FormLabel>
        {coverMediaId && (
          <Stack
            sx={{
              position: "relative",
              width: "100%",
              height: "150px",
              mb: 1,
              borderRadius: "md",
              overflow: "hidden",
              bg: "neutral.100",
            }}
          >
            <MediaThumb mediaId={coverMediaId} alt="Cover preview" />
          </Stack>
        )}
        <Button
          variant="outlined"
          component="label"
          sx={{ alignSelf: "flex-start" }}
          disabled={mediaUpload.isPending}
        >
          {mediaUpload.isPending ? "Uploading…" : "Upload cover"}
          <input
            type="file"
            accept="image/*"
            hidden
            ref={fileInputRef}
            onChange={handleCoverUpload}
          />
        </Button>
      </FormControl>

      <Button
        type="submit"
        variant="solid"
        size="lg"
        loading={update.isPending}
      >
        Save changes
      </Button>
    </Stack>
  );
}

export default SettingsTab;
