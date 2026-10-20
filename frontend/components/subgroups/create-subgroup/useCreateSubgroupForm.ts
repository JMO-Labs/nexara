"use client";
/**
 * @file components/subgroups/create-subgroup/useCreateSubgroupForm.ts
 * @brief State, slug validation and submit logic for CreateSubgroupModal.
 */
import * as React from "react";
import { useCreateSubgroup } from "@/hooks/useSubgroups";
import { useMediaUpload } from "@/hooks/useMediaUpload";
import { slugify, isValidSlugFormat } from "@/lib/slug";
import { getSubgroup } from "@/lib/api/subgroups";
import { searchAll } from "@/lib/api/search";
import type { SearchResultItem } from "@/lib/api/search";

export type JoinPolicy = "open" | "invite_only" | "admin_approval";
export type SlugStatus = "valid" | "invalid_format" | "taken" | "checking";
export interface OwnerUser {
  id: string;
  display_name?: string;
}

/**
 * @brief Form controller for the create-group modal.
 * @param onClose called after a successful create
 * @return form state and handlers
 */
export function useCreateSubgroupForm(onClose: () => void) {
  const create = useCreateSubgroup();
  const mediaUpload = useMediaUpload();

  const [name, setName] = React.useState("");
  const [slug, setSlug] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [joinPolicy, setJoinPolicy] = React.useState<JoinPolicy>("open");
  const [slugTouched, setSlugTouched] = React.useState(false);
  const [slugStatus, setSlugStatus] = React.useState<SlugStatus>("valid");
  const [coverMediaId, setCoverMediaId] = React.useState<string | null>(null);
  const [assignOwner, setAssignOwner] = React.useState(false);
  const [selectedOwner, setSelectedOwner] = React.useState<OwnerUser | null>(
    null,
  );
  const [ownerQuery, setOwnerQuery] = React.useState("");
  const [ownerSuggestions, setOwnerSuggestions] = React.useState<
    SearchResultItem[]
  >([]);
  const slugTimer = React.useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );

  // Auto-slug on name change unless user has manually edited
  React.useEffect(() => {
    if (!slugTouched && name) {
      setSlug(slugify(name));
      setSlugStatus("valid");
    }
  }, [name, slugTouched]);

  // Slug format validation + debounced uniqueness check
  React.useEffect(() => {
    if (!slug) {
      setSlugStatus("valid");
      return;
    }
    if (!isValidSlugFormat(slug)) {
      setSlugStatus("invalid_format");
      return;
    }
    setSlugStatus("checking");
    if (slugTimer.current) clearTimeout(slugTimer.current);
    slugTimer.current = setTimeout(async () => {
      try {
        await getSubgroup(slug);
        setSlugStatus("taken");
      } catch {
        // 404 or other error means slug is available
        setSlugStatus("valid");
      }
    }, 400);
  }, [slug]);

  // Owner search with debounce
  React.useEffect(() => {
    if (!ownerQuery.trim()) {
      setOwnerSuggestions([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const resp = await searchAll(ownerQuery, { types: ["users"] });
        setOwnerSuggestions(resp.items);
      } catch {
        setOwnerSuggestions([]);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [ownerQuery]);

  const uploadCover = async (file: File) => {
    try {
      setCoverMediaId(await mediaUpload.mutateAsync(file));
    } catch {
      // Error handled by useMediaUpload
    }
  };

  const toggleAssignOwner = () => {
    if (assignOwner) {
      setSelectedOwner(null);
      setOwnerQuery("");
    }
    setAssignOwner(!assignOwner);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (slugStatus !== "valid") return;
    await create.mutateAsync({
      name,
      slug,
      description: description || null,
      join_policy: joinPolicy,
      cover_media_id: coverMediaId,
      initial_owner_id: selectedOwner?.id,
    });
    setName("");
    setSlug("");
    setDescription("");
    setSlugTouched(false);
    setCoverMediaId(null);
    setAssignOwner(false);
    setSelectedOwner(null);
    setOwnerQuery("");
    onClose();
  };

  return {
    name,
    setName,
    slug,
    setSlug: (v: string) => {
      setSlug(v);
      setSlugTouched(true);
    },
    slugStatus,
    description,
    setDescription,
    joinPolicy,
    setJoinPolicy,
    coverMediaId,
    setCoverMediaId,
    uploadCover,
    uploading: mediaUpload.isPending,
    assignOwner,
    toggleAssignOwner,
    selectedOwner,
    setSelectedOwner,
    ownerQuery,
    setOwnerQuery,
    ownerSuggestions,
    submit,
    submitting: create.isPending,
    canSubmit: slugStatus === "valid" && !!name.trim() && !!slug.trim(),
  };
}
