"use client";
/**
 * @file components/admin/AdminSection.tsx
 * @brief Body of the /app/admin index route: renders the tab named by ?tab=.
 *        Gate, header and nav live in AdminShell.
 */
import { useSearchParams } from "next/navigation";
import { Panel } from "@/components/ui/page";
import { MetricsTab } from "./MetricsTab";
import { UsersTab } from "./UsersTab";
import { InvitesTab } from "./InvitesTab";
import { SsoTab } from "./SsoTab";
import { InterestsTab } from "./InterestsTab";
import { PromptsTab } from "./PromptsTab";
import { BrandingTab } from "./BrandingTab";
import { AIConfigTab } from "./AIConfigTab";
import { AuditLogTab } from "./AuditLogTab";
import { AdminSettingsTab } from "./AdminSettingsTab";
import { ShoppingTab } from "./ShoppingTab";
import { EmailTab } from "./EmailTab";
import { SystemTab } from "./system/SystemTab";
import { AlertsTab } from "./AlertsTab";
import { EmailRepliesTab } from "./EmailRepliesTab";
import { FeaturesTab } from "./FeaturesTab";
import { SecurityPolicy } from "./SecurityPolicy";
import { SigninsTab } from "./SigninsTab";

const SECTIONS: Record<string, () => React.JSX.Element | null> = {
  metrics: MetricsTab,
  users: UsersTab,
  invites: InvitesTab,
  sso: SsoTab,
  security: SecurityPolicy,
  signins: SigninsTab,
  interests: InterestsTab,
  prompts: PromptsTab,
  branding: BrandingTab,
  ai: AIConfigTab,
  shopping: ShoppingTab,
  email: EmailTab,
  system: SystemTab,
  alerts: AlertsTab,
  "email-reply": EmailRepliesTab,
  features: FeaturesTab,
  "audit-log": AuditLogTab,
  settings: AdminSettingsTab,
};

/** @brief Sections whose body has no surface of its own. */
const FLAT = new Set(["users", "sso", "branding"]);

/**
 * @brief Active admin tab body (defaults to metrics).
 * @return section content
 */
export function AdminSection() {
  const tab = useSearchParams().get("tab") || "metrics";
  const id = SECTIONS[tab] ? tab : "metrics";
  const Body = SECTIONS[id];
  // Bodies without their own cards sit on a glass panel.
  if (FLAT.has(id))
    return (
      <Panel as="div">
        <Body />
      </Panel>
    );
  return <Body />;
}
