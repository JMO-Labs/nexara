/**
 * @file lib/api/posts.ts
 * @brief Posts/comments/reactions REST endpoints.
 */
import { apiGet, apiPost, apiPut, apiDelete, seg } from "./client";

export interface PostAuthor {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

export interface PostMedia {
  id: string;
  url: string;
  thumbnail_url: string | null;
  mime_type: string;
  width: number | null;
  height: number | null;
}

export interface ReactionSummary {
  emoji: string;
  count: number;
  reacted_by_me: boolean;
}

export interface PollVoter {
  id: string;
  display_name: string;
  avatar_url: string | null;
}

export interface PollOption {
  id: string;
  label: string;
  image_media_id: string | null;
  position: number;
  vote_count: number;
  voters: PollVoter[];
}

export interface Poll {
  id: string;
  post_id: string | null;
  poll_type: "single" | "multiple" | "yes_no" | "photo";
  question: string;
  options: PollOption[];
  is_anonymous: boolean;
  result_visibility: "after_vote" | "always" | "after_expiry";
  expires_at: string | null;
  closed: boolean;
  total_votes: number;
  user_vote: string[] | null;
  created_at: string;
}

export interface LinkPreview {
  id: string;
  url: string;
  og_title: string | null;
  og_description: string | null;
  og_image: string | null;
  og_site_name: string | null;
  provider_type: string | null;
  provider_id: string | null;
}

export interface Post {
  id: string;
  content: string;
  author: PostAuthor;
  media: PostMedia[];
  poll: Poll | null;
  reactions: ReactionSummary[];
  comment_count: number;
  created_at: string;
  updated_at: string;
  subgroup_id: string | null;
  subgroup_name: string | null;
  subgroup_slug: string | null;
  /** Set when the post is a kudos. */
  recipient_id?: string | null;
  recipient?: {
    id: string;
    display_name: string;
    avatar_url: string | null;
  } | null;
  is_bookmarked?: boolean;
  is_prompt_post?: boolean;
  is_prompt_summary?: boolean;
  reply_to_prompt_id?: string | null;
  source_prompt_post_id?: string | null;
  link_previews?: LinkPreview[];
}

export interface Comment {
  id: string;
  content: string;
  author: PostAuthor;
  parent_id: string | null;
  created_at: string;
  replies: Comment[];
}

export interface Cursor<T> {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface CreatePostBody {
  content: string;
  media_ids?: string[];
  poll?: {
    question: string;
    poll_type?: "single" | "multiple" | "yes_no" | "photo";
    options: { label: string; image_media_id?: string }[];
    expires_at?: string;
    is_anonymous?: boolean;
    result_visibility?: "after_vote" | "always" | "after_expiry";
  };
  reply_to_prompt_id?: string;
  subgroup_id?: string | null;
}

export interface ReactionResponse {
  action: "added" | "removed";
  emoji: string;
  count: number;
}

export interface ListFeedParams {
  cursor?: string | null;
  limit?: number;
  subgroup_id?: string;
}

const POSTS = "/api/v1/posts";

export const listFeed = (params?: ListFeedParams | null, limit = 20) => {
  const qs = new URLSearchParams({ limit: String(params?.limit ?? limit) });
  if (params?.cursor) qs.set("cursor", params.cursor);
  if (params?.subgroup_id) qs.set("subgroup_id", params.subgroup_id);
  return apiGet<Cursor<Post>>(`${POSTS}?${qs}`);
};

export const getPost = (id: string) => apiGet<Post>(`${POSTS}/${seg(id)}`);

export const createPost = (body: CreatePostBody) => apiPost<Post>(POSTS, body);

export const updatePost = (id: string, content: string) =>
  apiPut<Post>(`${POSTS}/${seg(id)}`, { content });

export const deletePost = (id: string) =>
  apiDelete<{ message: string }>(`${POSTS}/${seg(id)}`);

export const listComments = (
  postId: string,
  cursor?: string | null,
  limit = 20,
) => {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (cursor) qs.set("cursor", cursor);
  return apiGet<Cursor<Comment>>(`${POSTS}/${seg(postId)}/comments?${qs}`);
};

export const createComment = (
  postId: string,
  content: string,
  parent_id?: string,
) =>
  apiPost<Comment>(`${POSTS}/${seg(postId)}/comments`, { content, parent_id });

export const togglePostReaction = (postId: string, emoji: string) =>
  apiPost<ReactionResponse>(`${POSTS}/${seg(postId)}/reactions`, { emoji });

export const toggleCommentReaction = (
  postId: string,
  commentId: string,
  emoji: string,
) =>
  apiPost<ReactionResponse>(
    `${POSTS}/${seg(postId)}/comments/${seg(commentId)}/reactions`,
    { emoji },
  );
