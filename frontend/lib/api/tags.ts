/**
 * @file lib/api/tags.ts
 * @brief Tags: who is tagged on a post/comment/photo, photo tagging, removal,
 *        a person's Tagged feed and @username lookup.
 */
import { apiDelete, apiGet, apiPost, seg } from "./client";
import type { Post } from "./posts";
import type { UserSummary } from "./users";

export type TagTarget = "post" | "comment" | "media";

export interface Tag {
  id: string;
  tagged_by: string | null;
  user: UserSummary | null;
  household: {
    id: string;
    name: string;
    kind: "person" | "pet";
    photo_media_id: string | null;
  } | null;
}

export interface TaggedPage {
  kind: "posts" | "photos";
  posts: Post[];
  media_ids: string[];
  next_before: string | null;
}

export const listTags = (type: TagTarget, id: string) =>
  apiGet<Tag[]>(`/api/v1/tags/${type}/${seg(id)}`);

export const tagPhoto = (
  mediaId: string,
  who: { user_id: string } | { household_id: string },
) => apiPost<Tag[]>(`/api/v1/media/${seg(mediaId)}/tags`, who);

export const removeTag = (tagId: string) =>
  apiDelete<{ message: string }>(`/api/v1/tags/${seg(tagId)}`);

export const getTagged = (
  userId: string,
  kind: "posts" | "photos",
  before?: string | null,
) => {
  const qs = new URLSearchParams({ kind });
  if (before) qs.set("before", before);
  return apiGet<TaggedPage>(`/api/v1/users/${seg(userId)}/tagged?${qs}`);
};

export const lookupUsername = (username: string) =>
  apiGet<UserSummary>(
    `/api/v1/users/lookup?${new URLSearchParams({ username })}`,
  );
