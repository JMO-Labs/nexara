"use client";
/**
 * @file components/admin/AdminTabs.tsx
 * @brief Main admin panel with tabbed interface. Deep-linkable via ?tab=.
 *        Enforces admin role requirement.
 */
import { useRouter, useSearchParams } from "next/navigation";
import { useSession } from "@/stores/session";
import { Tabs, TabList, Tab, TabPanel } from "@/components/ui";
import { AdminNotice } from "./AdminState";
import { MetricsTab } from "./MetricsTab";
import { UsersTab } from "./UsersTab";
import { InvitesTab } from "./InvitesTab";
import { SsoTab } from "./SsoTab";
import { InterestsTab } from "./InterestsTab";
import { AuditLogTab } from "./AuditLogTab";
import { AdminSettingsTab } from "./AdminSettingsTab";
import { PromptsTab } from "./PromptsTab";
import { BrandingTab } from "./BrandingTab";
import { AIConfigTab } from "./AIConfigTab";

const TABS = [
  { id: "metrics", label: "Metrics" },
  { id: "users", label: "Users" },
  { id: "invites", label: "Invites" },
  { id: "sso", label: "SSO" },
  { id: "interests", label: "Interests" },
  { id: "prompts", label: "Prompts" },
  { id: "branding", label: "Branding" },
  { id: "ai", label: "AI" },
  { id: "audit-log", label: "Audit log" },
  { id: "settings", label: "Settings" },
];

const TOUR: Record<string, string> = {
  invites: "admin-invites",
  users: "admin-users",
  sso: "admin-sso",
};

export function AdminTabs() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const user = useSession((s) => s.user);

  const selectedTab = searchParams.get("tab") || "metrics";

  if (!user || user.role !== "admin") {
    return (
      <AdminNotice>
        Admin access required. Your current role is:{" "}
        {user?.role || "unauthenticated"}
      </AdminNotice>
    );
  }

  return (
    <Tabs
      value={selectedTab}
      onValueChange={(id) => router.push(`/app/admin?tab=${id}`)}
    >
      <div className="overflow-x-auto">
        <TabList aria-label="Admin sections" className="w-max">
          {TABS.map((tab) => (
            <Tab
              key={tab.id}
              value={tab.id}
              data-tour={TOUR[tab.id]}
              className="min-h-11 whitespace-nowrap"
            >
              {tab.label}
            </Tab>
          ))}
        </TabList>
      </div>
      <TabPanel value="metrics">
        <MetricsTab />
      </TabPanel>
      <TabPanel value="users">
        <UsersTab />
      </TabPanel>
      <TabPanel value="invites">
        <InvitesTab />
      </TabPanel>
      <TabPanel value="sso">
        <SsoTab />
      </TabPanel>
      <TabPanel value="interests">
        <InterestsTab />
      </TabPanel>
      <TabPanel value="prompts">
        <PromptsTab />
      </TabPanel>
      <TabPanel value="branding">
        <BrandingTab />
      </TabPanel>
      <TabPanel value="ai">
        <AIConfigTab />
      </TabPanel>
      <TabPanel value="audit-log">
        <AuditLogTab />
      </TabPanel>
      <TabPanel value="settings">
        <AdminSettingsTab />
      </TabPanel>
    </Tabs>
  );
}
