"use client";
/**
 * @file components/lists/ListDetailPanel.tsx
 * @brief One list in detail: Items, Members and Settings tabs. The title is
 *        rendered by the host (page header or reading pane), so this body
 *        only shows tabs. `embedded` drops the glass Panel wrapper.
 */
import { format } from "date-fns";
import { Panel } from "@/components/ui/page";
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
  /** Render without the glass Panel wrapper (inside a reading pane). */
  embedded?: boolean;
}

/** @brief "community" -> "Community". */
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

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
      <ul className="flex flex-col gap-2 text-sm">
        {data?.map((m) => (
          <li
            key={m.userId}
            className="glass-item flex gap-2 rounded-[20px] px-4 py-2.5"
          >
            <span className="truncate">{m.userId}</span>
            <span className="text-muted">{cap(m.role)}</span>
          </li>
        ))}
      </ul>
      <Button
        variant="secondary"
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
    ["Visibility", cap(list.visibility)],
    ["Status", cap(list.status)],
    [
      "Expires",
      list.expiresAt
        ? format(new Date(list.expiresAt), "EEE, MMM d, yyyy")
        : "Never",
    ],
  ];
  return (
    <div className="flex flex-col gap-3">
      <dl className="flex flex-col gap-2 text-sm">
        {rows.map(([k, v]) => (
          <div
            key={k}
            className="glass-item flex justify-between gap-4 rounded-[20px] px-4 py-2.5"
          >
            <dt className="text-muted">{k}</dt>
            <dd className="font-medium">{v}</dd>
          </div>
        ))}
      </dl>
      <Button
        variant="secondary"
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
export function ListDetailPanel({
  list,
  communityId,
  embedded,
}: ListDetailPanelProps) {
  const body = (
    <>
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
    </>
  );
  if (embedded) return <div className="flex flex-col gap-4">{body}</div>;
  return <Panel className="flex flex-col gap-4">{body}</Panel>;
}
