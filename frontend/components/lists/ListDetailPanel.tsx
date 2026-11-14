"use client";
/**
 * @file components/lists/ListDetailPanel.tsx
 * @brief One list in detail: Items, Members and Settings tabs.
 */
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/Tabs";
import { useListMembers } from "@/hooks/useListActions";
import type { List } from "@/lib/api/listTypes";
import { ListEditModal } from "./ListEditModal";
import { ListGrid } from "./ListGrid";
import { ListMemberManageModal } from "./ListMemberManageModal";

export interface ListDetailPanelProps {
  list: List;
  communityId: string;
}

/**
 * @brief Members tab body.
 * @param props listId
 * @return members section
 */
function MembersTab({ listId }: { listId: string }) {
  const { data } = useListMembers(listId);
  const [open, setOpen] = useState(false);
  return (
    <div className="flex flex-col gap-3">
      <ul className="flex flex-col gap-1 text-sm">
        {data?.map((m) => (
          <li key={m.userId} className="flex gap-2">
            <span className="truncate">{m.userId}</span>
            <span className="opacity-70">{m.role}</span>
          </li>
        ))}
      </ul>
      <Button
        variant="outline"
        className="self-start"
        onClick={() => setOpen(true)}
      >
        Manage members
      </Button>
      {open && (
        <ListMemberManageModal
          open
          onClose={() => setOpen(false)}
          listId={listId}
        />
      )}
    </div>
  );
}

/**
 * @brief Settings tab body: read-only summary and edit button.
 * @param props list, communityId
 * @return settings section
 */
function SettingsTab({ list, communityId }: ListDetailPanelProps) {
  const [open, setOpen] = useState(false);
  const rows: [string, string][] = [
    ["Visibility", list.visibility],
    ["Status", list.status],
    [
      "Expires",
      list.expiresAt ? new Date(list.expiresAt).toLocaleDateString() : "Never",
    ],
  ];
  return (
    <div className="flex flex-col gap-3">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="font-semibold">{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
      <Button
        variant="outline"
        className="self-start"
        onClick={() => setOpen(true)}
      >
        Edit list
      </Button>
      {open && (
        <ListEditModal
          open
          onClose={() => setOpen(false)}
          list={list}
          communityId={communityId}
        />
      )}
    </div>
  );
}

/**
 * @brief Tabbed list detail.
 * @param props see ListDetailPanelProps
 * @return section
 */
export function ListDetailPanel({ list, communityId }: ListDetailPanelProps) {
  return (
    <section
      className="flex flex-col gap-3"
      aria-labelledby={`list-${list.id}-title`}
    >
      <header className="flex items-center gap-2">
        <span
          aria-hidden
          className="size-3 rounded-full"
          style={{ backgroundColor: list.color ?? "var(--color-accent)" }}
        />
        <h2 id={`list-${list.id}-title`} className="text-lg font-semibold">
          {list.title}
        </h2>
      </header>
      {list.description && (
        <p className="text-sm opacity-80">{list.description}</p>
      )}
      <Tabs defaultValue="items">
        <TabList aria-label="List sections">
          <Tab value="items">Items</Tab>
          <Tab value="members">Members</Tab>
          <Tab value="settings">Settings</Tab>
        </TabList>
        <TabPanel value="items">
          <ListGrid listId={list.id} fieldSchema={list.fieldSchema} />
        </TabPanel>
        <TabPanel value="members">
          <MembersTab listId={list.id} />
        </TabPanel>
        <TabPanel value="settings">
          <SettingsTab list={list} communityId={communityId} />
        </TabPanel>
      </Tabs>
    </section>
  );
}
