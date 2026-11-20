"use client";
/**
 * @file components/layout/MoreSheet.tsx
 * @brief Bottom sheet listing overflow nav items and sign out (phone).
 */
import Link from "next/link";
import { LogOut } from "lucide-react";
import { Drawer } from "@/components/ui/Drawer";
import { useSession } from "@/stores/session";
import { useModals } from "@/stores/modals";
import { useSignOut } from "@/hooks/useSignOut";
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
  const setHelpOpen = useModals((s) => s.setKeyboardShortcutsOpen);
  const signOut = useSignOut();
  const onLogout = async () => {
    onClose();
    await signOut();
  };

  return (
    <Drawer open={open} onClose={onClose} title="More" side="bottom">
      <ul className="m-0 list-none p-0">
        {[...PHONE_EXTRA_NAV, ...visibleNav(MORE_NAV, admin)].map(
          ({ label, href, action, Icon }) => (
            <li key={label}>
              {action === "help" || !href ? (
                <button
                  type="button"
                  className={ROW}
                  onClick={() => {
                    onClose();
                    setHelpOpen(true);
                  }}
                >
                  <Icon aria-hidden className="size-5" />
                  <span>{label}</span>
                </button>
              ) : (
                <Link href={href} onClick={onClose} className={ROW}>
                  <Icon aria-hidden className="size-5" />
                  <span>{label}</span>
                </Link>
              )}
            </li>
          ),
        )}
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
