"use client";
/**
 * @file components/members/AboutCard.tsx
 * @brief Profile "About" card: contact rows, social glyphs, birthday,
 *        skills, availability, dietary, emergency contact and a vCard
 *        download. Shows only what the API returned for this viewer.
 */
import * as React from "react";
import Link from "next/link";
import {
  Cake,
  Clock,
  Download,
  Globe,
  HeartPulse,
  Mail,
  MapPin,
  Phone,
  Utensils,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { Panel } from "@/components/ui/page";
import type { UserProfile } from "@/lib/api/users";
import { birthdayText, mapsUrl, socialFor, toVCard } from "@/lib/profile";

function Row({
  icon: Icon,
  label,
  children,
}: {
  icon: LucideIcon;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <li className="flex items-start gap-3">
      <span className="glass-item grid size-9 shrink-0 place-items-center rounded-full">
        <Icon className="size-4 text-muted" aria-hidden />
      </span>
      <div className="min-w-0 pt-0.5">
        <p className="text-xs text-muted">{label}</p>
        <div className="text-sm break-words">{children}</div>
      </div>
    </li>
  );
}

const linkCls = "underline-offset-2 hover:underline";

/**
 * @brief About card.
 * @param profile viewer-filtered profile
 * @param isSelf own profile (shows an edit hint when empty)
 * @return panel
 */
export function AboutCard({
  profile: p,
  isSelf,
}: {
  profile: UserProfile;
  isSelf: boolean;
}) {
  const links = [
    ...(p.website_url ? [{ label: "", url: p.website_url }] : []),
    ...(p.links ?? []),
  ];
  const socials = links.filter((l) => socialFor(l.url));
  const sites = links.filter((l) => !socialFor(l.url));
  const ec = p.emergency_contact;
  const hasContact = !!(p.phone || p.contact_email || p.address);
  const empty =
    !hasContact &&
    !links.length &&
    !p.birthday &&
    !p.skills?.length &&
    !p.availability &&
    !p.dietary &&
    !ec;

  const download = () => {
    const blob = new Blob([toVCard(p)], { type: "text/vcard" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${p.display_name.replace(/[^\w -]/g, "") || "contact"}.vcf`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <Panel as="section" aria-label="About" title="About">
      {empty ? (
        <p className="text-sm text-muted">
          {isSelf ? (
            <>
              Add your phone, links, birthday and more in{" "}
              <Link href="/app/settings?tab=profile" className="underline">
                Settings
              </Link>
              . You choose who sees each one.
            </>
          ) : (
            `${p.display_name.split(" ")[0]} hasn't shared any details with you yet.`
          )}
        </p>
      ) : (
        <div className="flex flex-col gap-5">
          {socials.length > 0 && (
            <ul className="flex flex-wrap gap-2" aria-label="Social profiles">
              {socials.map((l) => {
                const icon = socialFor(l.url)!;
                return (
                  <li key={l.url}>
                    <a
                      href={l.url}
                      target="_blank"
                      rel="noopener noreferrer nofollow"
                      aria-label={l.label || icon.title}
                      title={l.label || icon.title}
                      className="glass-item grid size-10 place-items-center rounded-full hover:text-[var(--brand)]"
                      style={
                        { "--brand": `#${icon.hex}` } as React.CSSProperties
                      }
                    >
                      <svg
                        viewBox="0 0 24 24"
                        className="size-[18px] fill-current"
                        aria-hidden
                      >
                        <path d={icon.path} />
                      </svg>
                    </a>
                  </li>
                );
              })}
            </ul>
          )}
          <ul className="flex flex-col gap-3.5">
            {p.phone && (
              <Row icon={Phone} label="Phone">
                <a
                  href={`tel:${p.phone.replace(/[^\d+]/g, "")}`}
                  className={linkCls}
                >
                  {p.phone}
                </a>
              </Row>
            )}
            {p.contact_email && (
              <Row icon={Mail} label="Email">
                <a href={`mailto:${p.contact_email}`} className={linkCls}>
                  {p.contact_email}
                </a>
              </Row>
            )}
            {p.address && (
              <Row icon={MapPin} label="Address">
                <span className="whitespace-pre-line">{p.address}</span>{" "}
                <a
                  href={mapsUrl(p.address)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-1 text-xs text-[var(--nx-blue)] hover:underline"
                >
                  Open in Maps
                </a>
              </Row>
            )}
            {p.birthday && (
              <Row icon={Cake} label="Birthday">
                {birthdayText(p.birthday)}
              </Row>
            )}
            {sites.map((l) => (
              <Row key={l.url} icon={Globe} label={l.label || "Website"}>
                <a
                  href={l.url}
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                  className={linkCls}
                >
                  {l.url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "")}
                </a>
              </Row>
            ))}
            {p.availability && (
              <Row icon={Clock} label="Usually available">
                {p.availability}
              </Row>
            )}
            {p.dietary && (
              <Row icon={Utensils} label="Dietary needs">
                {p.dietary}
              </Row>
            )}
            {ec && (
              <Row icon={HeartPulse} label="Emergency contact">
                {ec.name}
                {ec.relation ? ` (${ec.relation})` : ""} ·{" "}
                <a
                  href={`tel:${ec.phone.replace(/[^\d+]/g, "")}`}
                  className={linkCls}
                >
                  {ec.phone}
                </a>
              </Row>
            )}
          </ul>
          {!!p.skills?.length && (
            <div>
              <p className="mb-2 flex items-center gap-1.5 text-xs text-muted">
                <Wrench className="size-3.5" aria-hidden /> Can help with
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {p.skills.map((s) => (
                  <li
                    key={s}
                    className="glass-item rounded-full px-3 py-1 text-sm"
                  >
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {hasContact && (
            <button
              type="button"
              onClick={download}
              className="glass-item flex items-center justify-center gap-2 self-start rounded-full px-4 py-2 text-sm font-medium"
            >
              <Download className="size-4" aria-hidden /> Add to contacts
            </button>
          )}
        </div>
      )}
    </Panel>
  );
}
