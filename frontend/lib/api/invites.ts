/**
 * @file lib/api/invites.ts
 * @brief Invite management API endpoints.
 */
import { apiGet, apiPost, apiDelete } from "./client";

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
export const listInvites = () => apiGet<InviteResponse[]>("/api/v1/invites");

/**
 * @brief Create a new invite.
 * @param email Email address to invite
 * @param role Role to assign (admin, member, viewer)
 * @return InviteCreateResponse
 */
export const createInvite = (email: string, role: string) =>
  apiPost<InviteCreateResponse>("/api/v1/invites", { email, role });

/**
 * @brief Revoke an invite.
 * @param inviteId Invite ID
 * @return MessageResponse
 */
export const revokeInvite = (inviteId: string) =>
  apiDelete<MessageResponse>(`/api/v1/invites/${inviteId}`);
