/**
 * @file lib/api/adminEmailReply.ts
 * @brief Admin reply-by-email (IMAP mailbox) settings. Password is write-only.
 */
import { apiGet, apiPost, apiPut } from "./client";

export interface EmailReplySettings {
  imap_host: string;
  imap_port: number;
  imap_user: string;
  reply_address: string;
  has_password: boolean;
  /** Every field is filled in (the feature flag is separate). */
  configured: boolean;
}

export type EmailReplyUpdate = Partial<{
  imap_host: string;
  imap_port: number;
  imap_user: string;
  imap_password: string;
  reply_address: string;
}>;

export const EMAIL_REPLY_URL = "/api/v1/admin/email-reply";

/** @brief Saved settings (the password is never returned). */
export const getEmailReply = () => apiGet<EmailReplySettings>(EMAIL_REPLY_URL);
/** @brief Save settings; '' clears a text field. */
export const putEmailReply = (body: EmailReplyUpdate) =>
  apiPut<EmailReplySettings>(EMAIL_REPLY_URL, body);
/** @brief Log in to the mailbox and select the inbox. */
export const testEmailReply = () =>
  apiPost<{ success: boolean; message: string }>(`${EMAIL_REPLY_URL}/test`);
