/**
 * @file components/chat/chat-layout/helpers.ts
 * @brief Pure helpers for ChatLayout: last-channel storage, default pick, titles.
 */
import type { ChatChannel, DmThread } from "@/lib/api/chat";

const LAST_CHANNEL_KEY = "chat.lastChannelId";
const DENSITY_KEY = "chat.density";

export type Density = "comfortable" | "compact";

/** @brief Read the saved message density; "comfortable" by default. */
export function readDensity(): Density {
  if (typeof window === "undefined") return "comfortable";
  try {
    return window.localStorage.getItem(DENSITY_KEY) === "compact"
      ? "compact"
      : "comfortable";
  } catch {
    return "comfortable";
  }
}

/** @brief Persist the message density; silently skips on failure. */
export function writeDensity(d: Density): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(DENSITY_KEY, d);
  } catch {
    /* storage unavailable */
  }
}

/** @brief Read the last-used channel id; null when storage is unavailable. */
export function readLastChannel(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(LAST_CHANNEL_KEY);
  } catch {
    return null;
  }
}

/** @brief Persist the last-used channel id; silently skips on failure. */
export function writeLastChannel(id: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LAST_CHANNEL_KEY, id);
  } catch {
    /* storage unavailable (private mode, quota) */
  }
}

/**
 * @brief Pick the channel to open on bare /app/chat.
 * @param channels known channels
 * @param dms known DM threads
 * @param preferred last-used id
 * @return channel id or null
 */
export function pickDefaultChannel(
  channels: ChatChannel[],
  dms: DmThread[],
  preferred: string | null,
): string | null {
  if (preferred) {
    const inChannels = channels.some((c) => c.id === preferred);
    const inDms = dms.some((d) => d.channel_id === preferred);
    if (inChannels || inDms) return preferred;
  }
  const community = channels.find(
    (c) => c.channel_type === "community" && c.subgroup_id === null,
  );
  return community?.id ?? null;
}

/**
 * @brief Header title for a conversation.
 * @return peer name, "# channel" or "Conversation"
 */
export function resolveTitle(
  channels: ChatChannel[],
  dms: DmThread[],
  id: string,
): string {
  const dm = dms.find((d) => d.channel_id === id);
  if (dm) return dm.peer.display_name;
  const ch = channels.find((c) => c.id === id);
  if (ch) return ch.channel_type === "direct" ? ch.name : `# ${ch.name}`;
  return "Conversation";
}

/** @brief Human label for a non-open socket status. */
export function statusLabel(status: string): string | undefined {
  if (status === "connecting") return "Connecting…";
  if (status === "error") return "Connection error, retrying.";
  if (status === "closed") return "Disconnected, reconnecting.";
  return undefined;
}

/** @brief True on md+ viewports (two-pane layout). */
export function isDesktop(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(min-width: 768px)").matches
  );
}

/**
 * @brief Grid classes for chat panes: stacked < md, 2 panes at md,
 *        3 panes (with details) only at lg.
 * @param showDetails whether the details pane is open
 * @return class string
 */
export function gridClass(showDetails: boolean): string {
  const base =
    "bg-bg grid min-h-0 flex-1 grid-cols-1 overflow-hidden md:grid-cols-[280px_1fr]";
  return showDetails ? `${base} lg:grid-cols-[280px_1fr_320px]` : base;
}
