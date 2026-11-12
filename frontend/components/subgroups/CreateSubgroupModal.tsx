"use client";
/**
 * @file components/subgroups/CreateSubgroupModal.tsx
 * @brief Modal to create a new subgroup with auto-slug, cover upload, and
 *        optional initial owner. State lives in useCreateSubgroupForm.
 */
import * as React from "react";
import {
  Button,
  Modal,
  Input,
  Textarea,
  Select,
  Option,
} from "@/components/ui";
import { CoverField } from "./create-subgroup/CoverField";
import { OwnerPicker } from "./create-subgroup/OwnerPicker";
import {
  useCreateSubgroupForm,
  type JoinPolicy,
} from "./create-subgroup/useCreateSubgroupForm";

const SLUG_ERRORS = {
  invalid_format:
    "Must start with a letter or number, contain only letters, numbers, dashes, or underscores.",
  taken: "This slug is taken.",
} as const;

/**
 * @brief New-group dialog.
 * @param props open flag and close callback
 * @return modal element
 */
export function CreateSubgroupModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const f = useCreateSubgroupForm(onClose);
  const slugError =
    f.slugStatus === "invalid_format" || f.slugStatus === "taken"
      ? SLUG_ERRORS[f.slugStatus]
      : undefined;
  const slugHint =
    f.slugStatus === "checking" ? "Checking availability…" : "Available";

  return (
    <Modal open={open} onClose={onClose} title="New group">
      <form className="flex flex-col gap-4" onSubmit={f.submit}>
        <Input
          label="Name"
          value={f.name}
          onChange={(e) => f.setName(e.target.value)}
          required
        />
        <Input
          label="Slug"
          value={f.slug}
          onChange={(e) => f.setSlug(e.target.value)}
          error={slugError}
          hint={slugHint}
          pattern="^[a-z0-9][a-z0-9_\-]*$"
          required
        />
        <Textarea
          label="Description"
          rows={3}
          value={f.description}
          onChange={(e) => f.setDescription(e.target.value)}
        />
        <Select
          label="Join policy"
          value={f.joinPolicy}
          onValueChange={(v) => f.setJoinPolicy(v as JoinPolicy)}
        >
          <Option value="open">Open</Option>
          <Option value="invite_only">Invite only</Option>
          <Option value="admin_approval">Admin approval</Option>
        </Select>
        <CoverField
          mediaId={f.coverMediaId}
          uploading={f.uploading}
          onUpload={f.uploadCover}
          onRemove={() => f.setCoverMediaId(null)}
        />
        <OwnerPicker
          enabled={f.assignOwner}
          onToggle={f.toggleAssignOwner}
          query={f.ownerQuery}
          onQueryChange={f.setOwnerQuery}
          suggestions={f.ownerSuggestions}
          selected={f.selectedOwner}
          onSelect={f.setSelectedOwner}
          onClear={() => f.setSelectedOwner(null)}
        />
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="ghost"
            className="min-h-11"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            className="min-h-11"
            loading={f.submitting}
            disabled={!f.canSubmit}
          >
            Create
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default CreateSubgroupModal;
