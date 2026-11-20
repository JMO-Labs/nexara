"use client";
/**
 * @file components/admin/AdminShell.tsx
 * @brief Admin frame: gate, PageHeader and grouped SideNavs beside the
 *        active section. Used by app/app/admin/layout.tsx for all routes.
 */
import { useLayoutEffect, useRef, type ReactNode } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { PageHeader, SideNav, TwoPane } from "@/components/ui/page";
import { AdminGate } from "./AdminGate";
import { ADMIN_GROUPS, ADMIN_ITEMS, adminActiveId } from "./adminNav";

/** @brief Onboarding tour targets keyed by item id. */
const TOUR: Record<string, string> = {
  invites: "admin-invites",
  users: "admin-users",
  sso: "admin-sso",
};

/**
 * @brief Grouped nav (one SideNav per group, with a visible group label).
 * @param activeId current item id
 * @return nav stack
 */
function AdminNav({ activeId }: { activeId: string }) {
  const ref = useRef<HTMLDivElement>(null);
  // SideNav cannot forward attributes; tag tour targets after mount.
  useLayoutEffect(() => {
    for (const it of ADMIN_ITEMS) {
      if (!TOUR[it.id]) continue;
      ref.current
        ?.querySelector(`a[href="${it.href}"]`)
        ?.setAttribute("data-tour", TOUR[it.id]);
    }
  });
  // Phone shows one horizontal row; bring the active pill into view.
  useLayoutEffect(() => {
    ref.current
      ?.querySelector<HTMLElement>('[aria-current="page"]')
      ?.scrollIntoView?.({ inline: "center", block: "nearest" });
  }, [activeId]);
  return (
    <div
      ref={ref}
      className="flex flex-col gap-3 max-md:flex-row max-md:gap-2 max-md:overflow-x-auto max-md:pb-1 max-md:[mask-image:linear-gradient(to_right,black_88%,transparent)] max-md:[scrollbar-width:none] max-md:[&::-webkit-scrollbar]:hidden"
    >
      {ADMIN_GROUPS.map((g) => (
        <div
          key={g.label}
          className="flex flex-col gap-1 max-md:shrink-0 max-md:[&>nav]:flex-nowrap"
        >
          <p
            aria-hidden="true"
            className="mt-1 px-3 text-[13px] font-medium text-muted max-md:hidden"
          >
            {g.label}
          </p>
          <SideNav items={g.items} activeId={activeId} label={g.label} />
        </div>
      ))}
    </div>
  );
}

/**
 * @brief Admin page frame.
 * @param children active section content
 * @return gated admin layout
 */
export function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const tab = useSearchParams().get("tab");
  const activeId = adminActiveId(pathname, tab);
  const current = ADMIN_ITEMS.find((i) => i.id === activeId);
  return (
    <AdminGate>
      <PageHeader title="Admin" />
      <TwoPane aside={<AdminNav activeId={activeId} />} asideWidth={240}>
        {current && (
          <div className="mb-3 px-1">
            <h2 className="text-lg font-medium text-ink">{current.label}</h2>
            <p className="text-[15px] text-muted">{current.description}</p>
          </div>
        )}
        {children}
      </TwoPane>
    </AdminGate>
  );
}
