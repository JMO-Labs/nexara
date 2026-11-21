/**
 * @file components/subgroups/hub/SettingsTab.tsx
 * @brief Group settings tab: details, accent colour, logo URL and cover
 *        (upload or link via CoverPicker; saved immediately).
 */
"use client";

import * as React from "react";
import { Input, Textarea, Select, Option, Button } from "@/components/ui";
import { useUpdateSubgroup } from "@/hooks/useSubgroups";
import { CoverPicker } from "@/components/media/CoverPicker";
import { groupColor } from "@/lib/groupColor";
import type { SubgroupDetail, UpdateSubgroupBody } from "@/lib/api/subgroups";

export interface SettingsTabProps {
  subgroup: SubgroupDetail;
}

export function SettingsTab({ subgroup }: SettingsTabProps) {
  const canManage =
    subgroup.my_role === "owner" || subgroup.my_role === "moderator";
  const update = useUpdateSubgroup(subgroup.slug);
  const [accent, setAccent] = React.useState(subgroup.accent_color ?? "");
  const [name, setName] = React.useState(subgroup.name);
  const [description, setDescription] = React.useState(
    subgroup.description ?? "",
  );
  const [joinPolicy, setJoinPolicy] = React.useState<
    UpdateSubgroupBody["join_policy"]
  >(subgroup.join_policy);
  const [isPrivate, setIsPrivate] = React.useState(subgroup.is_private);
  const [avatarUrl, setAvatarUrl] = React.useState(subgroup.avatar_url ?? "");
  const [coverMediaId, setCoverMediaId] = React.useState<string | null>(
    subgroup.cover_media_id ?? null,
  );

  if (!canManage) {
    return (
      <p className="text-muted">
        You don&apos;t have permission to manage group settings.
      </p>
    );
  }

  const accentError =
    accent !== "" && !/^#[0-9a-fA-F]{6}$/.test(accent)
      ? "Use a hex color like #C6B4F5."
      : undefined;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (accentError) return;
    update.mutate({
      accent_color: accent === "" ? null : accent,
      name,
      description,
      join_policy: joinPolicy,
      is_private: isPrivate,
      avatar_url: avatarUrl.trim() || null,
    });
  };

  return (
    <form className="flex max-w-xl flex-col gap-6" onSubmit={submit}>
      <Input
        label="Group name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />

      <Textarea
        label="Description"
        rows={3}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />

      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-semibold">Join policy</span>
        <Select
          label="Join policy"
          value={joinPolicy ?? "open"}
          onValueChange={(v) =>
            setJoinPolicy(v as UpdateSubgroupBody["join_policy"])
          }
        >
          <Option value="open">Open (anyone can join)</Option>
          <Option value="invite_only">Invite only</Option>
          <Option value="admin_approval">Admin approval required</Option>
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-semibold">Private group</span>
        <Select
          label="Private group"
          value={isPrivate ? "true" : "false"}
          onValueChange={(v) => setIsPrivate(v === "true")}
        >
          <Option value="false">Visible to all members</Option>
          <Option value="true">Visible only to members</Option>
        </Select>
        <p className="text-sm text-muted">
          Private groups only appear to members in the directory.
        </p>
      </div>

      <div className="flex items-end gap-3">
        <input
          type="color"
          aria-label="Accent color picker"
          value={
            accentError || accent === ""
              ? groupColor(subgroup.id, null)
              : accent
          }
          onChange={(e) => setAccent(e.target.value)}
          className="size-11 shrink-0 cursor-pointer rounded-xl"
        />
        <div className="flex-1">
          <Input
            label="Accent color"
            value={accent}
            maxLength={7}
            error={accentError}
            hint="Hex, e.g. #C6B4F5. Leave empty to use the community color."
            onChange={(e) => setAccent(e.target.value)}
          />
        </div>
      </div>

      <Input
        label="Logo (avatar URL)"
        value={avatarUrl}
        onChange={(e) => setAvatarUrl(e.target.value)}
        placeholder="https://example.com/logo.png"
      />

      <CoverPicker
        mediaId={coverMediaId}
        onChange={(id) => {
          setCoverMediaId(id);
          update.mutate({ cover_media_id: id });
        }}
      />

      <Button type="submit" size="lg" loading={update.isPending}>
        Save changes
      </Button>
    </form>
  );
}

export default SettingsTab;
