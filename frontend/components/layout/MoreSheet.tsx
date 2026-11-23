"use client";
/**
 * @file components/layout/MoreSheet.tsx
 * @brief Bottom sheet listing overflow nav items and sign out (phone).
 */
import Link from "next/link";
import { LogOut } from "lucide-react";
import { Drawer } from "@/components/ui/Drawer";
import { useSession } from "@/stores/session";
import { useSignOut } from "@/hooks/useSignOut";
import { useFeature } from "@/hooks/useFeature";
import { MORE_NAV, PHONE_EXTRA_NAV, isAdmin, visibleNav } from "./navItems";

const ROW =
  "flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-ink hover:bg-[var(--nx-item)]";

/**
 * @brief More sheet.
 * @param props open state and close handler
 * @return drawer element
 */
export function MoreSheet({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const admin = useSession((s) => isAdmin(s.user));
  const signOut = useSignOut();
  const capsules = useFeature("time_capsules");
  const recipes = useFeature("recipes");
  const expenses = useFeature("expenses");
  const tree = useFeature("family_tree");
  const newsletter = useFeature("newsletter");
  const onLogout = async () => {
    onClose();
    await signOut();
  };

  return (
    <Drawer open={open} onClose={onClose} title="More" side="bottom">
      <ul className="m-0 list-none p-0">
        {[...PHONE_EXTRA_NAV, ...visibleNav(MORE_NAV, admin)]
          .filter((i) => capsules || i.href !== "/app/capsules")
          .filter((i) => recipes || i.href !== "/app/recipes")
          .filter((i) => expenses || i.href !== "/app/expenses")
          .filter((i) => newsletter || i.href !== "/app/newsletter")
          .filter((i) => tree || i.href !== "/app/family")
          .map(({ label, href, Icon }) => (
            <li key={label}>
              <Link href={href} onClick={onClose} className={ROW}>
                <Icon aria-hidden className="size-5" />
                <span>{label}</span>
              </Link>
            </li>
          ))}
        <li>
          <button type="button" onClick={onLogout} className={ROW}>
            <LogOut aria-hidden className="size-5" />
            <span>Sign out</span>
          </button>
        </li>
      </ul>
    </Drawer>
  );
}
