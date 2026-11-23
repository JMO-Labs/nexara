/**
 * @file lib/api/adminEmail.ts
 * @brief Admin outgoing-email (SMTP) settings. Password is write-only.
 */
import { apiGet, apiPost, apiPut } from "./client";

export type SmtpSecurity = "starttls" | "ssl" | "none";

export interface EmailSettings {
  host: string;
  port: number;
  security: SmtpSecurity;
  user: string;
  from_addr: string;
  from_name: string;
  auth: "password" | "google_oauth";
  has_password: boolean;
  has_google_refresh: boolean;
  google_client_id: string;
  has_google_client_secret: boolean;
  google_env_client: boolean;
  configured: boolean;
  last_ok_at: string | null;
  last_error: string | null;
}

export type EmailUpdate = Partial<{
  host: string;
  port: number;
  security: SmtpSecurity;
  user: string;
  password: string;
  from_addr: string;
  from_name: string;
  auth: "password" | "google_oauth";
  google_client_id: string;
  google_client_secret: string;
}>;

export const EMAIL_URL = "/api/v1/admin/email";

/** @brief Saved settings (the password is never returned). */
export const getEmail = () => apiGet<EmailSettings>(EMAIL_URL);
/** @brief Save settings; '' clears a text field. */
export const putEmail = (body: EmailUpdate) =>
  apiPut<EmailSettings>(EMAIL_URL, body);
/** @brief Send a test message to `to`. */
export const testEmail = (to: string) =>
  apiPost<{ ok: boolean; error: string | null }>(`${EMAIL_URL}/test`, { to });
/** @brief Google consent URL; the browser navigates there to connect the account. */
export const googleStart = () =>
  apiGet<{ url: string }>(`${EMAIL_URL}/google/start`);
