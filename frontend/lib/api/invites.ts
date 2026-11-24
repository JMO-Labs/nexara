/**
 * @file lib/api/invites.ts
 * @brief Invite management API endpoints.
 */
import { apiGet, apiPost, apiDelete, seg } from "./client";

/**
 * @brief Invite response item.
 */
export interface InviteResponse {
  id: string;
  email: string;
  role: string;
  created_at: Date;
  expires_at: Date;
  used_at: Date | null;
  code: string;
}

/**
 * @brief Invite creation response.
 */
export interface InviteCreateResponse {
  id: string;
  code: string;
  email: string;
  role: string;
}

/**
 * @brief Message response.
 */
export interface MessageResponse {
  message: string;
}

/**
 * @brief List all pending invites.
 * @return Array of InviteResponse
 */
export const listInvites = () =>
  apiGet<InviteResponse[]>("/api/v1/admin/invites");

/**
 * @brief Create a new invite.
 * @param email Email address to invite
 * @param role Role to assign (admin, member, viewer)
 * @return InviteCreateResponse
 */
export const createInvite = (email: string, role: string, age_group?: string) =>
  apiPost<InviteCreateResponse>("/api/v1/admin/invites", {
    email,
    role,
    ...(age_group ? { age_group } : {}),
  });

/**
 * @brief Revoke an invite.
 * @param inviteId Invite ID
 * @return MessageResponse
 */
export const revokeInvite = (inviteId: string) =>
  apiDelete<MessageResponse>(`/api/v1/admin/invites/${seg(inviteId)}`);
