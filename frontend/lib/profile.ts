/**
 * @file lib/profile.ts
 * @brief Profile helpers: privacy levels, social-link brand detection,
 *        maps links and vCard export (only what the viewer was sent).
 */
import {
  siBluesky,
  siFacebook,
  siGithub,
  siInstagram,
  siMastodon,
  siPinterest,
  siReddit,
  siSnapchat,
  siThreads,
  siTiktok,
  siTwitch,
  siWhatsapp,
  siX,
  siYoutube,
  type SimpleIcon,
} from "simple-icons";
import type { UserProfile } from "@/lib/api/users";

export type ProfileLevel = "private" | "groups" | "community";

export const LEVEL_LABEL: Record<ProfileLevel, string> = {
  private: "Only me",
  groups: "My groups",
  community: "Everyone",
};

const BRANDS: [RegExp, SimpleIcon][] = [
  [/(^|\.)instagram\.com$/, siInstagram],
  [/(^|\.)(facebook|fb)\.com$/, siFacebook],
  [/(^|\.)(x|twitter)\.com$/, siX],
  [/(^|\.)tiktok\.com$/, siTiktok],
  [/(^|\.)(youtube\.com|youtu\.be)$/, siYoutube],
  [/(^|\.)github\.com$/, siGithub],
  [/(^|\.)pinterest\.[a-z.]+$/, siPinterest],
  [/(^|\.)threads\.(net|com)$/, siThreads],
  [/(^|\.)bsky\.app$/, siBluesky],
  [/(^|\.)reddit\.com$/, siReddit],
  [/(^|\.)twitch\.tv$/, siTwitch],
  [/(^|\.)(wa\.me|whatsapp\.com)$/, siWhatsapp],
  [/(^|\.)snapchat\.com$/, siSnapchat],
];

/**
 * @brief Brand icon for a social URL (Mastodon by /@user path), or null.
 * @param url link
 * @return simple-icons entry or null for plain websites
 */
export function socialFor(url: string): SimpleIcon | null {
  let u: URL;
  try {
    u = new URL(url);
  } catch {
    return null;
  }
  const host = u.hostname.replace(/^www\./, "");
  for (const [re, icon] of BRANDS) if (re.test(host)) return icon;
  return /^\/@[\w.]+$/.test(u.pathname) ? siMastodon : null;
}

/** @brief Map search link for an address (works on every platform). */
export const mapsUrl = (address: string) =>
  `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;

const CTRL = /[\u0000-\u0009\u000b-\u001f\u007f]/g;
/** @brief vCard text escape: any line break -> \n, other controls dropped. */
const esc = (v: string) =>
  v
    .replace(/\r\n|\r|\n/g, "\n")
    .replace(CTRL, "")
    .replace(/\\/g, "\\\\")
    .replace(/\n/g, "\\n")
    .replace(/([,;])/g, "\\$1");

/** @brief True for absolute http(s) URLs only (never javascript:, data:, ...). */
export function isHttpUrl(url: string): boolean {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

/**
 * @brief vCard 3.0 text from the (already privacy-filtered) profile.
 * @param p profile as the viewer received it
 * @return .vcf content
 */
export function toVCard(p: UserProfile): string {
  const lines = ["BEGIN:VCARD", "VERSION:3.0", `FN:${esc(p.display_name)}`];
  const [first, ...rest] = p.display_name.split(" ");
  lines.push(`N:${esc(rest.join(" "))};${esc(first)};;;`);
  if (p.phone) lines.push(`TEL;TYPE=CELL:${esc(p.phone)}`);
  if (p.contact_email) lines.push(`EMAIL:${esc(p.contact_email)}`);
  if (p.address) lines.push(`ADR;TYPE=HOME:;;${esc(p.address)};;;;`);
  if (p.birthday && /^(\d{4}|-)-\d{2}-\d{2}$/.test(p.birthday))
    lines.push(`BDAY:${p.birthday}`);
  if (p.title) lines.push(`TITLE:${esc(p.title)}`);
  for (const l of [
    ...(p.website_url ? [{ url: p.website_url }] : []),
    ...(p.links ?? []),
  ].filter((l) => isHttpUrl(l.url)))
    lines.push(`URL:${esc(l.url)}`);
  if (p.bio) lines.push(`NOTE:${esc(p.bio)}`);
  lines.push("END:VCARD");
  return lines.join("\r\n") + "\r\n";
}

/**
 * @brief Human birthday text; "--MM-DD" means the year is hidden.
 * @param b ISO date or --MM-DD
 * @return e.g. "November 24" or "November 24, 1948"
 */
export function birthdayText(b: string): string {
  const hidden = b.startsWith("--");
  const [y, m, d] = hidden ? ["2000", ...b.slice(2).split("-")] : b.split("-");
  const date = new Date(Number(y), Number(m) - 1, Number(d));
  return date.toLocaleDateString(undefined, {
    month: "long",
    day: "numeric",
    ...(hidden ? {} : { year: "numeric" }),
  });
}
