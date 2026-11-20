"use client";
/**
 * @file components/inbox/InboxPage.tsx
 * @brief Inbox page: Notifications | Saved | Lists tabs bound to ?view=.
 */
import { useRouter, useSearchParams } from "next/navigation";
import { PageHeader, Toolbar, Segmented } from "@/components/ui/page";
import { ListsBrowseView } from "@/components/lists/pages/ListsBrowseView";
import { NotificationsView } from "./NotificationsView";
import { SavedView } from "./SavedView";

type View = "notifications" | "saved" | "lists";

const VIEWS: { value: View; label: string }[] = [
  { value: "notifications", label: "Notifications" },
  { value: "saved", label: "Saved" },
  { value: "lists", label: "Lists" },
];

/**
 * @brief Inbox page body; ?view= selects the tab (default notifications).
 * @return page element
 */
export function InboxPage() {
  const router = useRouter();
  const params = useSearchParams();
  const raw = params.get("view");
  const view: View = raw === "saved" || raw === "lists" ? raw : "notifications";

  const setView = (v: View) => {
    const next = new URLSearchParams(params.toString());
    if (v === "notifications") next.delete("view");
    else next.set("view", v);
    router.push(next.toString() ? `/app/inbox?${next}` : "/app/inbox");
  };

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Inbox"
        description="Notifications, saved posts and your lists."
      />
      <Toolbar>
        <Segmented
          label="Inbox view"
          value={view}
          onChange={setView}
          options={VIEWS}
        />
      </Toolbar>
      {view === "notifications" && <NotificationsView />}
      {view === "saved" && <SavedView />}
      {view === "lists" && <ListsBrowseView embedded />}
    </div>
  );
}
